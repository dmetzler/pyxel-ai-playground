"""Pix, the tutor, as a Strands harness agent working inside one game folder.

The harness gives Pix real file tools (read / write / edit) plus context
management and a per-game conversation saved on disk. On top of them we add
Pyxel tools: build and describe res.pyxres, and test-run the game headless.
All file access goes through a sandbox locked to the game's folder.
"""
import asyncio
import os
import sys
from pathlib import Path

from strands.models.openai import OpenAIModel
from strands.sandbox.not_a_sandbox_local_environment import NotASandboxLocalEnvironment
from strands.tools.decorator import tool
from strands_harness import create_harness

BACKEND_DIR = Path(__file__).parent
PROMPT = (BACKEND_DIR / "prompt_fr.md").read_text(encoding="utf-8")
RES_FILE = "res.pyxres"
SESSION_DIR = ".pix"  # inside each game folder: the agent's saved conversation


class GameFolderSandbox(NotASandboxLocalEnvironment):
    """The host filesystem, but only inside one game folder, and no shell."""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root.resolve()

    def _resolve_path(self, path: str) -> Path:
        p = (self.root / path).resolve()
        if p != self.root and self.root not in p.parents:
            raise PermissionError(f"Tu ne peux travailler que dans le dossier du jeu ({self.root}).")
        if SESSION_DIR in p.relative_to(self.root).parts:
            raise PermissionError("Ce dossier est réservé.")
        return p

    async def execute_streaming(self, *args, **kwargs):
        raise PermissionError("Pas de terminal ici : utilise les outils du jeu.")
        yield  # makes this an async generator, like the method it overrides

    async def execute_code_streaming(self, *args, **kwargs):
        raise PermissionError("Pas de terminal ici : utilise les outils du jeu.")
        yield


async def run_res_tool(*args: str, cwd: Path | None = None, timeout: float = 20) -> tuple[bool, str]:
    """Run res_tool.py in a subprocess with a time limit; returns (ok, output)."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(BACKEND_DIR / "res_tool.py"), *args,
        cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False, "Trop long : le script ne s'est pas arrêté (boucle infinie ?)."
    if proc.returncode != 0:
        return False, err.decode("utf-8", "replace")[-2000:]
    return True, out.decode("utf-8", "replace")


def _game_tools(game_dir: Path) -> list:
    res = game_dir / RES_FILE

    @tool
    async def modifier_ressources(script: str) -> str:
        """Run a Python script with headless Pyxel on the game's res.pyxres and save the result.

        The existing res.pyxres is loaded first, so anything the script does not touch is kept.
        `pyxel` is already imported and initialised: do not call pyxel.init, load, save or run.
        If the script fails, res.pyxres is left unchanged and the error is returned.
        Returns the new description of res.pyxres.

        Args:
            script: Python code drawing into pyxel.images / pyxel.tilemaps and composing
                pyxel.sounds / pyxel.musics.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            work, script_file = Path(tmp) / RES_FILE, Path(tmp) / "script.py"
            if res.is_file():
                work.write_bytes(res.read_bytes())
            script_file.write_text(script, encoding="utf-8")
            ok, out = await run_res_tool("build", str(work), str(script_file))
            if not ok:
                return "ERREUR, res.pyxres n'a pas été modifié :\n" + out
            res.write_bytes(work.read_bytes())
        ok, out = await run_res_tool("describe", str(res))
        return "res.pyxres enregistré. Contenu maintenant :\n" + out

    @tool
    async def voir_ressources() -> str:
        """Describe what is in the game's res.pyxres: sprites pixel by pixel, tilemaps, sounds, musics.

        The kid may have changed them in the Sprites tab, so look before changing them.
        """
        if not res.is_file():
            return "Le jeu n'a pas encore de res.pyxres."
        ok, out = await run_res_tool("describe", str(res))
        return out if ok else "ERREUR : " + out

    @tool
    async def tester_jeu() -> str:
        """Run game.py headless for about 2 seconds of frames (no keys pressed) and report any crash.

        Use it after every change to game.py or res.pyxres, and fix the code until it says OK.
        """
        ok, out = await run_res_tool("check", str(game_dir / "game.py"), cwd=game_dir)
        return out if ok else "LE JEU PLANTE :\n" + out

    return [modifier_ressources, voir_ressources, tester_jeu]


def make_model() -> OpenAIModel:
    # LiteLLM speaks the OpenAI API and maps the model name to an Anthropic model.
    return OpenAIModel(
        client_args={
            "base_url": os.getenv("LITELLM_BASE_URL", "http://localhost:4000").rstrip("/"),
            "api_key": os.getenv("LITELLM_API_KEY") or "none",
        },
        model_id=os.getenv("LITELLM_MODEL", "claude-3-5-sonnet"),
        params={"max_tokens": int(os.getenv("PIX_MAX_TOKENS", "16000"))},
    )


def make_agent(game_dir: Path):
    game_dir = game_dir.resolve()
    instructions = PROMPT + (
        f"\n\n## Les fichiers de CE jeu\n"
        f"- Le code : `{game_dir / 'game.py'}`\n"
        f"- Les ressources : `{game_dir / RES_FILE}` (avec les outils `voir_ressources` et `modifier_ressources`)\n"
    )
    return create_harness(
        model=make_model(),
        instructions=instructions,
        tools=_game_tools(game_dir),
        builtin_tools=["read", "write", "edit"],
        builtin_plugins=[],
        skills=False,
        memory=False,
        session={"id": "pix", "dir": str(game_dir / SESSION_DIR)},
        sandbox=GameFolderSandbox(game_dir),
        callback_handler=None,
    )


def has_session(game_dir: Path) -> bool:
    return (game_dir / SESSION_DIR).is_dir()
