"""FastAPI backend: saved games on disk, and Pix (a Strands harness agent) over SSE.

The browser never sees the API key. Pix works directly on games/<id>/game.py
and res.pyxres with tools; when a turn ends we send the files back to the UI.
"""
import asyncio
import base64
import io
import json
import os
import re
import shutil
import subprocess
import time
import unicodedata
import zipfile
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

import i18n
from i18n import t, tr

load_dotenv()

import pix_agent  # noqa: E402  (reads the .env loaded above)

LITELLM_MODEL = os.getenv("LITELLM_MODEL", "claude-3-5-sonnet")

# Each game is a folder: games/<id>/game.py (the code, runnable with real Pyxel too),
# chat.json (the conversation) and meta.json (its display name).
GAMES_DIR = Path(os.getenv("GAMES_DIR", Path(__file__).resolve().parent.parent / "games"))
GAMES_DIR.mkdir(parents=True, exist_ok=True)
GAME_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

app = FastAPI(title="Pyxel AI Playground backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; the Vite proxy means this is rarely hit directly
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(i18n.LangMiddleware)


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    # On a kid's message: the git commit from just before Pix's turn (to undo it).
    commit: str | None = None


class ChatRequest(BaseModel):
    game_id: str
    message: str
    # The code currently in the kid's editor (maybe not autosaved yet).
    current_code: str | None = None
    # Earlier conversation, used only to seed Pix for games created before it had a session.
    history: list[Message] = []


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "model": LITELLM_MODEL}


# One live agent per game, and one turn at a time per game.
_agents: dict[str, object] = {}
_locks: dict[str, asyncio.Lock] = {}


def _agent_for(game_id: str, d: Path, history: list[Message]):
    if game_id not in _agents:
        fresh = not pix_agent.has_session(d)
        agent = pix_agent.make_agent(d, _game_lang(d))
        if fresh and not agent.messages:
            agent.messages = _seed_messages(history)
        _agents[game_id] = agent
    return _agents[game_id]


def _seed_messages(history: list[Message]) -> list[dict]:
    """Old chat (text only) as Bedrock-style messages: starts with user, roles alternate."""
    out: list[dict] = []
    for m in history:
        if not m.content.strip() or (not out and m.role != "user"):
            continue
        if out and out[-1]["role"] == m.role:
            out[-1]["content"][0]["text"] += "\n\n" + m.content
        else:
            out.append({"role": m.role, "content": [{"text": m.content}]})
    if out and out[-1]["role"] == "user":
        out.pop()
    return out


@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    d = _game_dir(req.game_id)
    lock = _locks.setdefault(req.game_id, asyncio.Lock())
    lang = _game_lang(d)

    async def event_stream():
        async with lock:
            if req.current_code is not None:
                (d / "game.py").write_text(req.current_code, encoding="utf-8")
            # Save the kid's own changes first, so undoing Pix's turn keeps them.
            _ensure_repo(d)
            before = _commit(d, t(lang, "commit_student"))
            res_before = _read_resources(d)
            started: set[str] = set()
            reply = ""
            try:
                agent = _agent_for(req.game_id, d, req.history)
                async for ev in agent.stream_async(req.message):
                    if "data" in ev and isinstance(ev["data"], str):
                        reply += ev["data"]
                        yield _sse({"delta": ev["data"]})
                    elif ev.get("type") == "tool_use_stream":
                        tu = ev["current_tool_use"]
                        if tu.get("toolUseId") not in started:
                            started.add(tu.get("toolUseId"))
                            if reply and not reply.endswith("\n"):
                                reply += "\n\n"
                            yield _sse({"tool": tu.get("name")})
            except Exception as exc:  # report any agent/model failure to the kid's UI
                _agents.pop(req.game_id, None)
                yield _sse({"error": tr("pix_problem", error=f"{type(exc).__name__}: {exc}")[:800]})
            _commit(d, t(lang, "commit_pix", msg=" ".join(req.message.split())[:72]))
            # Save the turn now: the page may be closed before the UI autosaves.
            _append_chat(d, [
                Message(role="user", content=req.message, commit=before),
                *([Message(role="assistant", content=reply.rstrip())] if reply.strip() else []),
            ])
            res_after = _read_resources(d)
            yield _sse({
                "done": True,
                "commit": before,
                "code": (d / "game.py").read_text(encoding="utf-8"),
                "base_code": _base_code(d),
                "resources": res_after,
                "resources_changed": res_after != res_before,
            })

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/games/{game_id}/stop")
async def stop_chat(game_id: str) -> dict:
    """Stop Pix's running turn; what it already did is kept (and committed)."""
    _game_dir(game_id)
    agent = _agents.get(game_id)
    lock = _locks.get(game_id)
    # Strands clears its cancel flag only when a turn ends: cancelling between
    # turns would kill the next one before it starts.
    if agent is not None and lock is not None and lock.locked():
        agent.cancel()
    return {"ok": True}


class UndoRequest(BaseModel):
    commit: str


@app.post("/api/games/{game_id}/undo")
async def undo(game_id: str, req: UndoRequest) -> dict:
    """Put the game (code, resources, Pix's memory) back as it was at `commit`."""
    d = _game_dir(game_id)
    lock = _locks.setdefault(game_id, asyncio.Lock())
    if lock.locked():
        raise HTTPException(status_code=409, detail=tr("pix_busy"))
    lang = _game_lang(d)
    async with lock:
        if not COMMIT_RE.match(req.commit) or not (d / ".git").is_dir():
            raise HTTPException(status_code=400, detail=tr("unknown_version"))
        try:
            _git(d, "cat-file", "-e", f"{req.commit}^{{commit}}")
        except subprocess.CalledProcessError:
            raise HTTPException(status_code=400, detail=tr("unknown_version"))
        # Commit the old version on top instead of rewriting history, so an undo can be undone too.
        _commit(d, t(lang, "commit_student"))
        _git(d, "read-tree", "-u", "--reset", req.commit)
        _git(d, "clean", "-q", "-fd")
        _commit(d, t(lang, "commit_undo", commit=req.commit[:7]))
        # Pix's conversation lives in .pix/ (tracked): reload it from disk.
        _agents.pop(game_id, None)
        return {
            "code": (d / "game.py").read_text(encoding="utf-8"),
            "base_code": _base_code(d),
            "resources": _read_resources(d),
        }


# --- Git history: each game folder is its own repository --------------------

COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
# chat.json is the UI's copy of the conversation, saved all the time: not versioned.
GAME_GITIGNORE = "chat.json\n__pycache__/\n"


def _git(d: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=Pix", "-c", "user.email=pix@atelier.local",
         "-c", "safe.directory=*", *args],
        cwd=d, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _ensure_repo(d: Path) -> None:
    if (d / ".git").is_dir():
        return
    _git(d, "init", "-q", "-b", "main")
    (d / ".gitignore").write_text(GAME_GITIGNORE, encoding="utf-8")
    _commit(d, t(_game_lang(d), "commit_start"))


def _base_code(d: Path) -> str | None:
    """game.py before the last commit, so the editor can mark what that commit changed."""
    if not (d / ".git").is_dir():
        return None
    try:
        return subprocess.run(
            ["git", "-c", "safe.directory=*", "show", "HEAD~1:game.py"],
            cwd=d, check=True, capture_output=True, text=True,
        ).stdout
    except subprocess.CalledProcessError:  # first commit, or no game.py back then
        return None


def _commit(d: Path, message: str) -> str:
    """Commit everything if something changed; returns the current commit."""
    _git(d, "add", "-A")
    if _git(d, "status", "--porcelain"):
        _git(d, "commit", "-q", "-m", message)
    return _git(d, "rev-parse", "HEAD")



# --- Saved games ------------------------------------------------------------


class GameCreate(BaseModel):
    name: str
    code: str
    messages: list[Message]
    lang: Literal["fr", "en", "pl"] = "fr"


class GameSave(BaseModel):
    code: str
    messages: list[Message]


def _game_dir(game_id: str) -> Path:
    # The regex keeps ids to plain slugs, so a request can't escape GAMES_DIR.
    d = GAMES_DIR / game_id
    if not GAME_ID_RE.match(game_id) or not d.is_dir():
        raise HTTPException(status_code=404, detail=tr("game_not_found"))
    return d


def _read_meta(d: Path) -> dict:
    return json.loads((d / "meta.json").read_text(encoding="utf-8"))


def _game_lang(d: Path) -> str:
    """The game's language from meta.json; games made before languages existed are French."""
    try:
        return i18n.norm_lang(_read_meta(d).get("lang"))
    except (OSError, ValueError, AttributeError):
        return i18n.DEFAULT_LANG


def _new_game_id(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:50] or "jeu"
    game_id, n = base, 2
    while (GAMES_DIR / game_id).exists():
        game_id, n = f"{base}-{n}", n + 1
    return game_id


def _write_game(d: Path, code: str, messages: list[Message]) -> None:
    (d / "game.py").write_text(code, encoding="utf-8")
    _write_chat(d, messages)


def _write_chat(d: Path, messages: list[Message]) -> None:
    (d / "chat.json").write_text(
        json.dumps([m.model_dump(exclude_none=True) for m in messages], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _append_chat(d: Path, messages: list[Message]) -> None:
    f = d / "chat.json"
    old = [Message(**m) for m in json.loads(f.read_text(encoding="utf-8"))] if f.is_file() else []
    _write_chat(d, old + messages)


@app.get("/api/games")
async def list_games() -> list[dict]:
    games = []
    for d in GAMES_DIR.iterdir():
        meta, code = d / "meta.json", d / "game.py"
        if GAME_ID_RE.match(d.name) and meta.is_file() and code.is_file():
            m = json.loads(meta.read_text(encoding="utf-8"))
            games.append({"id": d.name, "name": m["name"], "lang": i18n.norm_lang(m.get("lang")),
                          "updated": code.stat().st_mtime})
    return sorted(games, key=lambda g: g["updated"], reverse=True)


@app.post("/api/games")
async def create_game(req: GameCreate) -> dict:
    name = req.name.strip()[:80] or t(req.lang, "default_name")
    game_id = _new_game_id(name)
    d = GAMES_DIR / game_id
    d.mkdir()
    (d / "meta.json").write_text(
        json.dumps({"name": name, "created": time.time(), "lang": req.lang}, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_game(d, req.code, req.messages)
    _ensure_repo(d)
    return {"id": game_id, "name": name}


@app.get("/api/games/{game_id}")
async def load_game(game_id: str) -> dict:
    d = _game_dir(game_id)
    return {
        "id": game_id,
        "name": _read_meta(d)["name"],
        "lang": _game_lang(d),
        "code": (d / "game.py").read_text(encoding="utf-8"),
        "base_code": _base_code(d),
        "messages": json.loads((d / "chat.json").read_text(encoding="utf-8")),
        "resources": _read_resources(d),
    }


class ResourcesSave(BaseModel):
    data: str  # base64 of the .pyxres file


RES_FILE = "res.pyxres"


def _read_resources(d: Path) -> str | None:
    f = d / RES_FILE
    return base64.b64encode(f.read_bytes()).decode() if f.is_file() else None


@app.put("/api/games/{game_id}/resources")
async def save_resources(game_id: str, req: ResourcesSave) -> dict:
    (_game_dir(game_id) / RES_FILE).write_bytes(base64.b64decode(req.data))
    return {"ok": True}


@app.put("/api/games/{game_id}")
async def save_game(game_id: str, req: GameSave) -> dict:
    _write_game(_game_dir(game_id), req.code, req.messages)
    return {"ok": True}


@app.delete("/api/games/{game_id}")
async def delete_game(game_id: str) -> dict:
    d = _game_dir(game_id)
    lock = _locks.get(game_id)
    if lock is not None and lock.locked():
        raise HTTPException(status_code=409, detail=tr("pix_busy_game"))
    shutil.rmtree(d)
    _agents.pop(game_id, None)
    _locks.pop(game_id, None)
    return {"ok": True}


@app.get("/api/games/{game_id}/export")
async def export_game(game_id: str) -> Response:
    d = _game_dir(game_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(d.rglob("*")):
            if f.is_file() and not f.is_symlink() and "__pycache__" not in f.parts:
                z.write(f, f.relative_to(d).as_posix())
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{game_id}.zip"'},
    )


MAX_IMPORT_BYTES = 50 * 1024 * 1024
MAX_UNZIPPED_BYTES = 200 * 1024 * 1024
# An imported .git must not be able to run commands: no hooks, a config with nothing in it.
SAFE_GIT_CONFIG = "[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n"


def _bad_zip(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def _zip_members(z: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, str]]:
    """(entry, path inside the game folder), refusing anything that could escape it."""
    entries = [i for i in z.infolist() if not i.is_dir()]
    if sum(i.file_size for i in entries) > MAX_UNZIPPED_BYTES:
        raise _bad_zip(tr("zip_too_big"))
    for i in entries:
        parts = i.filename.replace("\\", "/").split("/")
        is_link = (i.external_attr >> 16) & 0o170000 == 0o120000
        if i.filename.startswith(("/", "\\")) or ":" in parts[0] or ".." in parts or is_link:
            raise _bad_zip(tr("zip_bad_paths"))
    names = [i.filename.replace("\\", "/") for i in entries]
    if "game.py" in names:
        return list(zip(entries, names))
    # Everything inside one top folder (zipped from the file explorer): strip it.
    tops = {n.split("/")[0] for n in names}
    if len(tops) == 1 and all("/" in n for n in names):
        top = tops.pop()
        inner = [n[len(top) + 1:] for n in names]
        if "game.py" in inner:
            return list(zip(entries, inner))
    raise _bad_zip(tr("zip_no_game"))


@app.post("/api/games/import")
async def import_game(request: Request) -> dict:
    data = await request.body()
    if len(data) > MAX_IMPORT_BYTES:
        raise _bad_zip(tr("zip_too_big"))
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise _bad_zip(tr("zip_unreadable"))
    with z:
        members = _zip_members(z)
        name, lang = "", i18n.DEFAULT_LANG
        meta = next((i for i, p in members if p == "meta.json"), None)
        if meta is not None:
            try:
                old_meta = json.loads(z.read(meta))
                name = str(old_meta.get("name", "")).strip()[:80]
                lang = i18n.norm_lang(old_meta.get("lang"))
            except (ValueError, AttributeError):
                name, lang = "", i18n.DEFAULT_LANG
        if not name:
            first = members[0][0].filename.replace("\\", "/")
            name = first.split("/")[0] if "/" in first and not first.startswith(".") else t(lang, "imported_name")
        game_id = _new_game_id(name)
        d = GAMES_DIR / game_id
        d.mkdir()
        try:
            for info, path in members:
                target = d / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(info))
            (d / "meta.json").write_text(
                json.dumps({"name": name, "created": time.time(), "lang": lang}, ensure_ascii=False),
                encoding="utf-8",
            )
            if not (d / "chat.json").is_file():
                _write_chat(d, [])
            if (d / ".git").is_dir():
                shutil.rmtree(d / ".git" / "hooks", ignore_errors=True)
                (d / ".git" / "config").write_text(SAFE_GIT_CONFIG)
            _ensure_repo(d)
        except Exception:
            shutil.rmtree(d, ignore_errors=True)
            raise
    return {"id": game_id, "name": name}


@app.get("/api/games/{game_id}/story.pdf")
async def story_pdf(game_id: str) -> Response:
    d = _game_dir(game_id)
    from story import build_story_pdf

    pdf = await asyncio.to_thread(build_story_pdf, d)
    story_name = t(_game_lang(d), "story_file")
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{game_id}-{story_name}.pdf"'},
    )


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"
