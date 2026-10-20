import asyncio

import pix_agent


def run(*args, cwd=None):
    return asyncio.run(pix_agent.run_res_tool(*args, cwd=cwd))


def test_build_then_describe(tmp_path):
    res, script = tmp_path / "res.pyxres", tmp_path / "s.py"
    script.write_text(
        "pyxel.images[0].pset(1, 2, 8)\n"
        "pyxel.sounds[0].set('c2e2g2', 'p', '7', 'n', 20)\n"
        "pyxel.musics[0].set([0], [], [], [])\n"
    )
    ok, out = run("build", str(res), str(script))
    assert ok, out
    ok, out = run("describe", str(res))
    assert ok, out
    lines = out.splitlines()
    assert lines[0] == "images[0] u=0 v=0 (16x16) :"
    assert lines[3][1] == "8"  # row v=2, column u=1
    assert any(line.startswith("sounds[0] : notes=[") for line in lines)
    assert "musics[0] : [[0]]" in lines


def test_build_keeps_what_the_script_does_not_touch(tmp_path):
    res, s1, s2 = tmp_path / "res.pyxres", tmp_path / "a.py", tmp_path / "b.py"
    s1.write_text("pyxel.images[0].pset(0, 0, 7)\n")
    s2.write_text("pyxel.images[1].pset(0, 0, 9)\n")
    assert run("build", str(res), str(s1))[0]
    assert run("build", str(res), str(s2))[0]
    out = run("describe", str(res))[1]
    assert "images[0] u=0 v=0" in out and "images[1] u=0 v=0" in out


def test_build_error_is_reported(tmp_path):
    script = tmp_path / "s.py"
    script.write_text("pyxel.images[0].oops()\n")
    ok, out = run("build", str(tmp_path / "res.pyxres"), str(script))
    assert not ok
    assert "AttributeError" in out


def test_check_runs_the_game_headless(tmp_path):
    game = tmp_path / "game.py"
    game.write_text(
        "import pyxel\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        pyxel.init(160, 120)\n"
        "        self.n = 0\n"
        "        pyxel.run(self.update, self.draw)\n"
        "    def update(self):\n"
        "        self.n += 1\n"
        "    def draw(self):\n"
        "        pyxel.cls(self.n % 16)\n"
        "App()\n"
    )
    ok, out = run("check", str(game), cwd=tmp_path)
    assert ok, out
    assert out.startswith("OK")


def test_check_reports_a_crash_in_update(tmp_path):
    game = tmp_path / "game.py"
    game.write_text(
        "import pyxel\n"
        "pyxel.init(160, 120)\n"
        "def update():\n"
        "    if pyxel.frame_count > 3:\n"
        "        raise ValueError('boum')\n"
        "pyxel.run(update, lambda: pyxel.cls(0))\n"
    )
    ok, out = run("check", str(game), cwd=tmp_path)
    assert not ok
    assert "ValueError: boum" in out


def test_check_loads_resources_next_to_the_game(tmp_path):
    script = tmp_path / "s.py"
    script.write_text("pyxel.images[0].pset(0, 0, 3)\n")
    assert run("build", str(tmp_path / "res.pyxres"), str(script))[0]
    game = tmp_path / "game.py"
    game.write_text(
        "import pyxel\n"
        "pyxel.init(160, 120)\n"
        "pyxel.load('res.pyxres')\n"
        "assert pyxel.images[0].pget(0, 0) == 3\n"
        "pyxel.run(lambda: None, lambda: None)\n"
    )
    ok, out = run("check", str(game), cwd=tmp_path)
    assert ok, out


def test_infinite_loop_times_out(tmp_path):
    script = tmp_path / "s.py"
    script.write_text("while True:\n    pass\n")
    ok, out = asyncio.run(pix_agent.run_res_tool("build", str(tmp_path / "r.pyxres"), str(script), timeout=2))
    assert not ok
    assert out.startswith("Trop long")
