import json
import subprocess
import sys
from pathlib import Path

import pytest

import story

HERE = Path(__file__).resolve().parent.parent

STEP1 = "import pyxel\n\npyxel.init(40, 30)\n\ndef update():\n    pass\n\ndef draw():\n    pyxel.cls(1)\n\npyxel.run(update, draw)\n"
STEP2 = STEP1.replace("pyxel.cls(1)", "pyxel.cls(1)\n    pyxel.rect(10, 10, 8, 8, 10)")


def git(d: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=d,
                          check=True, capture_output=True, text=True).stdout.strip()


def commit(d: Path, code: str, msg: str) -> str:
    (d / "game.py").write_text(code)
    git(d, "add", "-A")
    git(d, "commit", "-q", "--allow-empty", "-m", msg)
    return git(d, "rev-parse", "HEAD")


@pytest.fixture
def story_game(tmp_path: Path) -> Path:
    d = tmp_path / "jeu"
    d.mkdir()
    git(d, "init", "-q", "-b", "main")
    (d / "meta.json").write_text(json.dumps({"name": "Mon jeu é"}))
    c0 = commit(d, "import pyxel\n", "Début")
    c1 = commit(d, STEP1, "Pix 1")
    commit(d, STEP2, "Pix 2")
    (d / "chat.json").write_text(json.dumps([
        {"role": "assistant", "content": "Salut !"},
        {"role": "user", "content": "Un écran bleu", "commit": c0},
        {"role": "assistant", "content": "Voilà **ton écran** 🎮"},
        {"role": "user", "content": "Un carré jaune", "commit": c1},
        {"role": "assistant", "content": "Fait !"},
    ]))
    return d


def test_story_pdf_has_one_step_per_kid_message(story_game: Path):
    steps = story._steps(story_game, json.loads((story_game / "chat.json").read_text()))
    assert [s["ask"] for s in steps] == ["Un écran bleu", "Un carré jaune"]
    assert steps[0]["answer"] == ["Voilà **ton écran** 🎮"]
    assert story._show(story_game, steps[1]["after"], "game.py").decode() == STEP2
    assert story.build_story_pdf(story_game).startswith(b"%PDF")


def test_extract_marks_only_changed_lines():
    rows = story._extract(STEP1, STEP2)
    added = [num for num, _src, is_new in rows if is_new]
    assert added == [10]
    assert story._extract(STEP1, STEP1) is None


def test_screenshot_is_three_times_the_game_size(tmp_path: Path):
    (tmp_path / "game.py").write_text(STEP2)
    out = tmp_path / "shot.png"
    subprocess.run([sys.executable, str(HERE / "res_tool.py"), "screenshot", str(tmp_path / "game.py"),
                    str(out), "5"], check=True, capture_output=True, timeout=30)
    head = out.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    assert (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")) == (120, 90)


def test_a_crashing_game_still_gives_a_pdf(story_game: Path):
    commit(story_game, "import pyxel\npyxel.init(40, 30)\nraise RuntimeError('boum')\n", "Cassé")
    assert story._screenshot(story_game, "HEAD") is None
    assert story.build_story_pdf(story_game).startswith(b"%PDF")
