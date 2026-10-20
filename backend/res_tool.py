"""Builds and describes a game's res.pyxres with headless Pyxel.

Run as a subprocess by app.py (so a buggy script can't take the server down):

    python res_tool.py build <res_file> <script_file>
        Load res_file if it exists, run the script (which draws into
        pyxel.images / tilemaps and composes pyxel.sounds / musics), save back.
    python res_tool.py describe <res_file>
        Print a compact text summary of the resources for the tutor.
    python res_tool.py check <game_file>
        Run the game headless for a few frames to catch crashes.
"""
import sys
from pathlib import Path

import pyxel

HEX = "0123456789abcdef"
CELL = 16  # sprites are laid out on a 16x16 grid in the image banks
MAX_CELLS = 16  # cells shown pixel by pixel in the description


def _init(res: Path) -> None:
    pyxel.init(160, 120, headless=True)
    if res.is_file():
        pyxel.load(str(res))


def build(res: Path, script: Path) -> None:
    _init(res)
    code = script.read_text(encoding="utf-8")
    exec(compile(code, "ressources", "exec"), {"__name__": "__main__", "pyxel": pyxel})
    pyxel.save(str(res))


def _cell_rows(img: pyxel.Image, cx: int, cy: int) -> list[str] | None:
    rows = [
        "".join(HEX[img.pget(cx + x, cy + y)] for x in range(CELL)) for y in range(CELL)
    ]
    return rows if any(r.strip("0") for r in rows) else None


def describe(res: Path) -> str:
    _init(res)
    out: list[str] = []
    shown = 0
    for bank in range(3):
        img = pyxel.images[bank]
        for cy in range(0, img.height, CELL):
            for cx in range(0, img.width, CELL):
                rows = _cell_rows(img, cx, cy)
                if rows is None:
                    continue
                if shown < MAX_CELLS:
                    out.append(f"images[{bank}] u={cx} v={cy} (16x16) :")
                    out.extend(rows)
                else:
                    out.append(f"images[{bank}] u={cx} v={cy} : dessin (non affiche)")
                shown += 1
    for i, tm in enumerate(pyxel.tilemaps):
        # The first screen of tiles (20x15 = 160x120 pixels), as tilemaps[i].set() expects.
        rows = [
            " ".join("%02x%02x" % tm.pget(x, y) for x in range(20)) for y in range(15)
        ]
        if any(r.replace("0000", "").strip() for r in rows):
            out.append(f"tilemaps[{i}] (imgsrc={tm.imgsrc}), premier ecran 20x15 tuiles :")
            out.extend(rows)
    for i, s in enumerate(pyxel.sounds):
        if s.notes:
            out.append(
                f"sounds[{i}] : notes={list(s.notes)} tones={list(s.tones)} "
                f"volumes={list(s.volumes)} effects={list(s.effects)} speed={s.speed}"
            )
    for i, m in enumerate(pyxel.musics):
        seqs = [list(seq) for seq in m.seqs]
        if any(seqs):
            out.append(f"musics[{i}] : {seqs}")
    return "\n".join(out) or "(fichier vide)"


def check(game: Path, frames: int = 60) -> str:
    """Run game.py headless for a few frames; raises on any crash."""
    real_init = pyxel.init

    def fake_run(update, draw):
        for _ in range(frames):
            update()
            draw()
        raise SystemExit(0)

    pyxel.init = lambda *a, **k: real_init(*a, **{**k, "headless": True})
    pyxel.run = fake_run
    # pyxel.init moves to the main script's folder (this file): keep the game's own folder.
    game = game.resolve()
    real_load = pyxel.load
    pyxel.load = lambda f, *a, **k: real_load(str(game.parent / f), *a, **k)
    code = game.read_text(encoding="utf-8")
    try:
        exec(compile(code, "game.py", "exec"), {"__name__": "__main__"})
    except SystemExit:
        pass
    return f"OK : le jeu tourne ({frames} images sans erreur, sans appuyer sur aucune touche)."


if __name__ == "__main__":
    cmd, res = sys.argv[1], Path(sys.argv[2])
    if cmd == "build":
        build(res, Path(sys.argv[3]))
    elif cmd == "describe":
        print(describe(res))
    elif cmd == "check":
        print(check(res))
    else:
        sys.exit(f"commande inconnue : {cmd}")
