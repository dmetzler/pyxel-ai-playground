"""Shared fixtures: a temporary games folder and a scripted model in place of LiteLLM.

Everything else is real: the FastAPI app, the Strands harness and its file tools,
git, and res_tool.py with headless Pyxel.
"""
import asyncio
import json
import sys
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from strands.models.model import Model

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module  # noqa: E402
import pix_agent  # noqa: E402

STARTER = 'import pyxel\n\npyxel.init(160, 120)\npyxel.run(lambda: None, lambda: pyxel.cls(1))\n'


class ScriptedModel(Model):
    """Answers each model call with the next scripted response.

    A response is a list of blocks: ("text", str) or ("tool", name, input).
    `gates[i]`, if set, is a threading.Event the model waits on before response i,
    and `started[i]` is set when call i begins, so a test can act mid-turn.
    """

    def __init__(self, responses: list[list[tuple]]):
        self.responses = list(responses)
        self.calls = 0
        self.gates: dict[int, threading.Event] = {}
        self.started: dict[int, threading.Event] = {}

    def update_config(self, **config):
        pass

    def get_config(self):
        return {}

    async def structured_output(self, *args, **kwargs):
        raise NotImplementedError
        yield

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        i = self.calls
        self.calls += 1
        self.started.setdefault(i, threading.Event()).set()
        if i in self.gates:
            assert await asyncio.to_thread(self.gates[i].wait, 10), "test never opened the gate"
        blocks = self.responses[i] if i < len(self.responses) else [("text", "Fini.")]
        yield {"messageStart": {"role": "assistant"}}
        uses_tool = False
        for n, block in enumerate(blocks):
            if block[0] == "text":
                yield {"contentBlockStart": {"start": {}}}
                yield {"contentBlockDelta": {"delta": {"text": block[1]}}}
            else:
                uses_tool = True
                _, name, tool_input = block
                yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"t{i}-{n}", "name": name}}}}
                yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(tool_input)}}}}
            yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use" if uses_tool else "end_turn"}}


@pytest.fixture
def games_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "GAMES_DIR", tmp_path)
    app_module._agents.clear()
    app_module._locks.clear()
    yield tmp_path
    app_module._agents.clear()
    app_module._locks.clear()


@pytest.fixture
def client(games_dir):
    with TestClient(app_module.app) as c:
        yield c


@pytest.fixture
def script(monkeypatch):
    """Call script(responses) to make Pix answer with them; returns the model."""
    models: list[ScriptedModel] = []

    def install(responses):
        model = ScriptedModel(responses)
        models.append(model)
        monkeypatch.setattr(pix_agent, "make_model", lambda: model)
        return model

    return install


@pytest.fixture
def game(client):
    """A new game with the starter code; returns its id."""
    r = client.post("/api/games", json={
        "name": "Mon Jeu",
        "code": STARTER,
        "messages": [{"role": "assistant", "content": "Salut !"}],
    })
    assert r.status_code == 200
    return r.json()["id"]


def sse_events(body: str) -> list[dict]:
    return [json.loads(line[5:]) for line in body.splitlines() if line.startswith("data:")]


def chat(client, game_id: str, message: str, code: str | None = None) -> list[dict]:
    r = client.post("/api/chat", json={"game_id": game_id, "message": message, "current_code": code})
    assert r.status_code == 200
    return sse_events(r.text)


def git_log(d: Path) -> list[str]:
    return app_module._git(d, "log", "--format=%s").splitlines()
