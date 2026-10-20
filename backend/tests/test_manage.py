import asyncio
import io
import sys
import types
import zipfile

import app as app_module
from conftest import STARTER, git_log


def make_zip(files: dict[str, bytes | str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def import_zip(client, data: bytes):
    return client.post("/api/games/import", content=data, headers={"Content-Type": "application/zip"})


def test_delete_removes_the_game(client, games_dir, game):
    assert client.delete(f"/api/games/{game}").json() == {"ok": True}
    assert not (games_dir / game).exists()
    assert client.get("/api/games").json() == []
    assert client.delete(f"/api/games/{game}").status_code == 404


def test_delete_while_pix_works_is_409(client, games_dir, game):
    lock = asyncio.Lock()
    app_module._locks[game] = lock
    asyncio.run(lock.acquire())
    r = client.delete(f"/api/games/{game}")
    assert r.status_code == 409
    assert (games_dir / game).is_dir()


def test_export_then_import_round_trips(client, games_dir, game):
    client.put(f"/api/games/{game}/resources", json={"data": "AAEC"})
    app_module._commit(games_dir / game, "Dessins")
    r = client.get(f"/api/games/{game}/export")
    assert r.headers["content-type"] == "application/zip"
    assert r.headers["content-disposition"] == f'attachment; filename="{game}.zip"'
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert {"game.py", "chat.json", "meta.json", "res.pyxres", ".git/HEAD"} <= set(names)

    imported = import_zip(client, r.content).json()
    assert imported == {"id": "mon-jeu-2", "name": "Mon Jeu"}
    copy = client.get("/api/games/mon-jeu-2").json()
    original = client.get(f"/api/games/{game}").json()
    for key in ("code", "messages", "resources", "name"):
        assert copy[key] == original[key]
    assert git_log(games_dir / "mon-jeu-2") == ["Dessins", "Début du jeu"]


def test_import_of_a_zipped_folder_without_meta(client, games_dir):
    r = import_zip(client, make_zip({"Mon Super Jeu/game.py": STARTER}))
    assert r.json() == {"id": "mon-super-jeu", "name": "Mon Super Jeu"}
    d = games_dir / "mon-super-jeu"
    assert (d / "game.py").read_text() == STARTER
    assert git_log(d) == ["Début du jeu"]
    assert client.get("/api/games/mon-super-jeu").json()["messages"] == []


def test_import_rejects_unsafe_or_empty_zips(client, games_dir):
    for files in [{"game.py": STARTER, "../evil.py": "x"}, {"/etc/x": "x", "game.py": ""}, {"readme.txt": "hi"}]:
        r = import_zip(client, make_zip(files))
        assert r.status_code == 400, files
    assert import_zip(client, b"not a zip").status_code == 400
    assert list(games_dir.iterdir()) == []
    assert not (games_dir.parent / "evil.py").exists()


def test_import_neutralizes_git_hooks_and_config(client, games_dir, game):
    exported = client.get(f"/api/games/{game}/export").content
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(exported)) as src, zipfile.ZipFile(buf, "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == ".git/config":
                data = b"[core]\n\tfsmonitor = touch /tmp/pwned\n"
            dst.writestr(info, data)
        dst.writestr(".git/hooks/post-commit", "#!/bin/sh\ntouch /tmp/pwned\n")
    new_id = import_zip(client, buf.getvalue()).json()["id"]
    d = games_dir / new_id
    assert not (d / ".git" / "hooks").exists()
    assert (d / ".git" / "config").read_text() == app_module.SAFE_GIT_CONFIG
    assert git_log(d) == ["Début du jeu"]


def test_story_pdf_route(client, game, monkeypatch):
    fake = types.ModuleType("story")
    fake.build_story_pdf = lambda d: b"%PDF-1.7 " + d.name.encode()
    monkeypatch.setitem(sys.modules, "story", fake)
    r = client.get(f"/api/games/{game}/story.pdf")
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == f'attachment; filename="{game}-histoire.pdf"'
    assert r.content == b"%PDF-1.7 " + game.encode()
