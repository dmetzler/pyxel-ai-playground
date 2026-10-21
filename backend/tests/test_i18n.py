import json
from pathlib import Path

import i18n
import pix_agent
import story
from conftest import STARTER, chat, git_log


def new_game(client, lang=None):
    body = {"name": "My Game", "code": STARTER, "messages": []}
    if lang is not None:
        body["lang"] = lang
    return client.post("/api/games", json=body)


def story_html(d: Path, monkeypatch) -> str:
    """The HTML the story PDF is rendered from (no PDF text-extraction tool needed)."""
    seen = []
    real = story.HTML

    def capture(string, **kwargs):
        seen.append(string)
        return real(string=string, **kwargs)

    monkeypatch.setattr(story, "HTML", capture)
    assert story.build_story_pdf(d).startswith(b"%PDF")
    return seen[0]


def test_create_with_lang_en_is_stored_and_returned(client, games_dir):
    r = new_game(client, "en")
    assert r.status_code == 200
    game_id = r.json()["id"]
    assert json.loads((games_dir / game_id / "meta.json").read_text())["lang"] == "en"
    assert client.get(f"/api/games/{game_id}").json()["lang"] == "en"
    assert [g["lang"] for g in client.get("/api/games").json()] == ["en"]


def test_lang_defaults_to_fr(client, games_dir):
    game_id = new_game(client).json()["id"]
    assert client.get(f"/api/games/{game_id}").json()["lang"] == "fr"
    assert git_log(games_dir / game_id) == ["Début du jeu"]


def test_invalid_lang_is_refused(client):
    assert new_game(client, "de").status_code == 422


def test_old_meta_without_lang_is_french(client, games_dir):
    game_id = new_game(client, "en").json()["id"]
    (games_dir / game_id / "meta.json").write_text(json.dumps({"name": "Old"}))
    assert client.get(f"/api/games/{game_id}").json()["lang"] == "fr"
    assert client.get("/api/games").json()[0]["lang"] == "fr"


def test_commit_messages_follow_the_game_lang(client, games_dir, script):
    script([[("text", "OK")]])
    game_id = new_game(client, "en").json()["id"]
    d = games_dir / game_id
    assert git_log(d) == ["Start of the game"]
    chat(client, game_id, "Make it blue", code=STARTER + "# mine\n")
    assert git_log(d) == ["Pix: Make it blue", "Student's changes", "Start of the game"]


def test_error_detail_follows_x_lang(client):
    r = client.get("/api/games/nope", headers={"X-Lang": "pl"})
    assert r.status_code == 404
    assert r.json()["detail"] == i18n.t("pl", "game_not_found") == "Nie znaleziono gry"
    assert client.get("/api/games/nope").json()["detail"] == "Jeu introuvable"
    assert client.get("/api/games/nope", headers={"X-Lang": "xx"}).json()["detail"] == "Jeu introuvable"


def test_import_keeps_a_valid_meta_lang(client):
    game_id = new_game(client, "pl").json()["id"]
    zipped = client.get(f"/api/games/{game_id}/export").content
    r = client.post("/api/games/import", content=zipped)
    assert r.status_code == 200
    assert client.get(f"/api/games/{r.json()['id']}").json()["lang"] == "pl"


def test_prompt_falls_back_to_french(monkeypatch, tmp_path):
    (tmp_path / "prompt_fr.md").write_text("FR", encoding="utf-8")
    (tmp_path / "prompt_en.md").write_text("EN", encoding="utf-8")
    monkeypatch.setattr(pix_agent, "BACKEND_DIR", tmp_path)
    monkeypatch.setattr(pix_agent, "PROMPT", "FR")
    assert pix_agent.load_prompt("en") == "EN"
    assert pix_agent.load_prompt("pl") == "FR"


def test_every_lang_has_every_key():
    keys = set(i18n.STRINGS["fr"])
    for lang in i18n.LANGS:
        assert set(i18n.STRINGS[lang]) == keys, lang


def test_story_pdf_in_english(client, games_dir, monkeypatch):
    game_id = new_game(client, "en").json()["id"]
    text = story_html(games_dir / game_id, monkeypatch)
    assert '<html lang="en">' in text
    assert "The full code of your game" in text
    assert "Keep going at home" in text
    assert "Le code complet" not in text
