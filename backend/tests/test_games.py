from conftest import STARTER, git_log


def test_create_list_load_save(client, games_dir):
    r = client.post("/api/games", json={"name": "  Ça Roule ! ", "code": STARTER, "messages": []})
    assert r.json() == {"id": "ca-roule", "name": "Ça Roule !"}

    # Same name again gets its own folder.
    assert client.post("/api/games", json={"name": "Ça roule", "code": "", "messages": []}).json()["id"] == "ca-roule-2"

    ids = [g["id"] for g in client.get("/api/games").json()]
    assert sorted(ids) == ["ca-roule", "ca-roule-2"]

    game = client.get("/api/games/ca-roule").json()
    assert game["code"] == STARTER
    assert game["messages"] == []
    assert game["resources"] is None
    assert game["base_code"] is None  # only the first commit so far

    msgs = [{"role": "user", "content": "coucou"}]
    assert client.put("/api/games/ca-roule", json={"code": "print(1)\n", "messages": msgs}).status_code == 200
    game = client.get("/api/games/ca-roule").json()
    assert game["code"] == "print(1)\n"
    assert game["messages"] == msgs


def test_new_game_is_a_git_repo(client, games_dir, game):
    d = games_dir / game
    assert (d / ".git").is_dir()
    assert git_log(d) == ["Début du jeu"]
    assert "chat.json" in (d / ".gitignore").read_text()


def test_resources_round_trip(client, game):
    assert client.put(f"/api/games/{game}/resources", json={"data": "AAEC"}).status_code == 200
    assert client.get(f"/api/games/{game}").json()["resources"] == "AAEC"


def test_unknown_or_unsafe_ids_are_404(client, game):
    for bad in ["nope", "..", "UPPER", "a_b", "-x"]:
        assert client.get(f"/api/games/{bad}").status_code == 404, bad
    assert client.put("/api/games/nope", json={"code": "", "messages": []}).status_code == 404
    assert client.post("/api/games/nope/undo", json={"commit": "abcdef1"}).status_code == 404
    assert client.post("/api/chat", json={"game_id": "../x", "message": "hi"}).status_code == 404
