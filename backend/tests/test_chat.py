import threading

import app as app_module
from conftest import STARTER, chat, git_log

NEW_CODE = 'import pyxel\n\npyxel.init(160, 120)\npyxel.run(lambda: None, lambda: pyxel.cls(0))\n'


def test_turn_edits_with_tools_and_is_committed(client, games_dir, game, script):
    d = games_dir / game
    script([
        [("text", "Je lis ton code."), ("tool", "read", {"path": str(d / "game.py")})],
        [("tool", "write", {"path": str(d / "game.py"), "content": NEW_CODE})],
        [("tool", "test_game", {})],
        [("text", "Le fond est noir maintenant !")],
    ])
    events = chat(client, game, "Mets le fond en noir", code=STARTER)

    assert [e["tool"] for e in events if "tool" in e] == ["read", "write", "test_game"]
    assert "".join(e.get("delta", "") for e in events) == "Je lis ton code.Le fond est noir maintenant !"
    assert not [e for e in events if "error" in e]
    done = events[-1]
    assert done["done"] and done["code"] == NEW_CODE
    assert done["base_code"] == STARTER
    assert done["resources_changed"] is False

    assert (d / "game.py").read_text() == NEW_CODE
    assert git_log(d) == ["Pix : Mets le fond en noir", "Début du jeu"]
    assert done["commit"] == app_module._git(d, "rev-parse", "HEAD~1")

    # The backend saves the turn itself, with the version to undo to.
    chat_json = client.get(f"/api/games/{game}").json()["messages"]
    assert chat_json[-2] == {"role": "user", "content": "Mets le fond en noir", "commit": done["commit"]}
    assert chat_json[-1]["role"] == "assistant"
    assert "Le fond est noir" in chat_json[-1]["content"]


def test_kid_edits_are_committed_before_pix(client, games_dir, game, script):
    script([[("text", "Rien à changer.")]])
    events = chat(client, game, "Ça va ?", code="print('moi')\n")
    d = games_dir / game
    assert git_log(d) == ["Pix : Ça va ?", "Modifications de l'élève", "Début du jeu"]
    assert app_module._git(d, "show", f"{events[-1]['commit']}:game.py") == "print('moi')"


def test_sandbox_keeps_pix_in_the_game_folder(client, games_dir, game, script):
    d = games_dir / game
    model = script([
        [("tool", "write", {"path": str(games_dir / "evil.py"), "content": "x"})],
        [("tool", "write", {"path": str(d / ".pix" / "evil.py"), "content": "x"})],
        [("text", "Ok.")],
    ])
    chat(client, game, "essaie")
    assert not (games_dir / "evil.py").exists()
    assert not (d / ".pix" / "evil.py").exists()
    results = [c["toolResult"] for m in app_module._agents[game].messages for c in m["content"] if "toolResult" in c]
    assert [r["status"] for r in results] == ["error", "error"]
    assert model.calls == 3


def test_model_failure_is_reported_and_still_ends(client, game, script):
    model = script([])

    async def broken(*args, **kwargs):
        raise RuntimeError("LiteLLM est parti")
        yield

    model.stream = broken
    events = chat(client, game, "hello")
    assert "LiteLLM est parti" in events[-2]["error"]
    assert events[-1]["done"] is True
    assert game not in app_module._agents  # a fresh agent next time


def test_undo_restores_code_and_keeps_history(client, games_dir, game, script):
    d = games_dir / game
    script([
        [("tool", "write", {"path": str(d / "game.py"), "content": NEW_CODE})],
        [("text", "Fait.")],
    ])
    commit = chat(client, game, "noir")[-1]["commit"]
    assert (d / "game.py").read_text() == NEW_CODE

    r = client.post(f"/api/games/{game}/undo", json={"commit": commit})
    assert r.status_code == 200
    assert r.json()["code"] == STARTER
    assert (d / "game.py").read_text() == STARTER
    # Undo is a new commit: the undone turn can still be found in the history.
    log = git_log(d)
    assert log[0].startswith("Annulation : retour à la version")
    assert "Pix : noir" in log
    assert app_module._git(d, "status", "--porcelain") == ""
    assert game not in app_module._agents


def test_undo_rejects_bad_commits(client, game):
    for bad in ["not-a-sha", "0000000", "--hard"]:
        r = client.post(f"/api/games/{game}/undo", json={"commit": bad})
        assert r.status_code == 400, bad


def test_undo_while_pix_works_is_409(client, games_dir, game, script):
    model = script([[("text", "Je réfléchis…")]])
    model.gates[0] = threading.Event()
    head = app_module._git(games_dir / game, "rev-parse", "HEAD")
    worker = threading.Thread(target=chat, args=(client, game, "long"))
    worker.start()
    assert model.started.setdefault(0, threading.Event()).wait(10)
    try:
        r = client.post(f"/api/games/{game}/undo", json={"commit": head})
        assert r.status_code == 409
    finally:
        model.gates[0].set()
        worker.join(10)


def test_stop_ends_the_running_turn(client, games_dir, game, script):
    model = script([
        [("text", "Je commence.")],
        [("text", "Jamais dit.")],
    ])
    model.responses[0] = [("text", "Je commence."), ("tool", "test_game", {})]
    model.gates[0] = threading.Event()
    result: dict = {}
    worker = threading.Thread(target=lambda: result.update(events=chat(client, game, "long")))
    worker.start()
    assert model.started.setdefault(0, threading.Event()).wait(10)
    assert client.post(f"/api/games/{game}/stop").status_code == 200
    model.gates[0].set()
    worker.join(10)
    text = "".join(e.get("delta", "") for e in result["events"])
    assert "Jamais dit" not in text
    assert result["events"][-1]["done"] is True


def test_stop_while_idle_does_not_cancel_the_next_turn(client, game, script):
    script([[("text", "Premier.")], [("text", "Deuxième !")]])
    chat(client, game, "un")
    # The kid clicks stop after Pix already finished (e.g. a slow click).
    assert client.post(f"/api/games/{game}/stop").status_code == 200
    events = chat(client, game, "deux")
    assert "".join(e.get("delta", "") for e in events) == "Deuxième !"
