"""FastAPI backend: saved games on disk, and Pix (a Strands harness agent) over SSE.

The browser never sees the API key. Pix works directly on games/<id>/game.py
and res.pyxres with tools; when a turn ends we send the files back to the UI.
"""
import asyncio
import base64
import json
import os
import re
import subprocess
import time
import unicodedata
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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
        agent = pix_agent.make_agent(d)
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

    async def event_stream():
        async with lock:
            if req.current_code is not None:
                (d / "game.py").write_text(req.current_code, encoding="utf-8")
            # Save the kid's own changes first, so undoing Pix's turn keeps them.
            _ensure_repo(d)
            before = _commit(d, "Modifications de l'élève")
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
                yield _sse({"error": f"Pix a eu un problème : {type(exc).__name__}: {exc}"[:800]})
            _commit(d, "Pix : " + " ".join(req.message.split())[:72])
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
        raise HTTPException(status_code=409, detail="Pix est encore en train de travailler.")
    async with lock:
        if not COMMIT_RE.match(req.commit) or not (d / ".git").is_dir():
            raise HTTPException(status_code=400, detail="Version inconnue")
        try:
            _git(d, "cat-file", "-e", f"{req.commit}^{{commit}}")
        except subprocess.CalledProcessError:
            raise HTTPException(status_code=400, detail="Version inconnue")
        # Commit the old version on top instead of rewriting history, so an undo can be undone too.
        _commit(d, "Modifications de l'élève")
        _git(d, "read-tree", "-u", "--reset", req.commit)
        _git(d, "clean", "-q", "-fd")
        _commit(d, f"Annulation : retour à la version {req.commit[:7]}")
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
    _commit(d, "Début du jeu")


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


class GameSave(BaseModel):
    code: str
    messages: list[Message]


def _game_dir(game_id: str) -> Path:
    # The regex keeps ids to plain slugs, so a request can't escape GAMES_DIR.
    d = GAMES_DIR / game_id
    if not GAME_ID_RE.match(game_id) or not d.is_dir():
        raise HTTPException(status_code=404, detail="Jeu introuvable")
    return d


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
            name = json.loads(meta.read_text(encoding="utf-8"))["name"]
            games.append({"id": d.name, "name": name, "updated": code.stat().st_mtime})
    return sorted(games, key=lambda g: g["updated"], reverse=True)


@app.post("/api/games")
async def create_game(req: GameCreate) -> dict:
    name = req.name.strip()[:80] or "Mon jeu"
    game_id = _new_game_id(name)
    d = GAMES_DIR / game_id
    d.mkdir()
    (d / "meta.json").write_text(
        json.dumps({"name": name, "created": time.time()}, ensure_ascii=False), encoding="utf-8"
    )
    _write_game(d, req.code, req.messages)
    _ensure_repo(d)
    return {"id": game_id, "name": name}


@app.get("/api/games/{game_id}")
async def load_game(game_id: str) -> dict:
    d = _game_dir(game_id)
    return {
        "id": game_id,
        "name": json.loads((d / "meta.json").read_text(encoding="utf-8"))["name"],
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


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"
