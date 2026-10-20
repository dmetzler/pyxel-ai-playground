# Pyxel AI Playground

A friendly web app where middle-school kids build a game with the [Pyxel](https://github.com/kitao/pyxel) retro game engine by **chatting** with an AI tutor. The tutor builds the game step by step, explains every change in plain language, and the kid watches it come alive in the preview — or peeks at (and tweaks) the code.

```
┌──────────────────┬────────────────────────────────────┐
│  Discussion      │  Aperçu | Code | Sprites           │
│  (AI chat)       │  (live game, code, Pyxel editor)   │
└──────────────────┴────────────────────────────────────┘
```

## How it works

- **Frontend** (`frontend/`): Vite + React + TypeScript. Left pane = chat with the AI tutor. Right pane = tabs for the live **Preview** (real Pyxel running in the browser via Pyodide + the Pyxel wheel, in a sandboxed iframe) and an editable **Code** view.
- **Backend** (`backend/`): FastAPI. Pix is a **[Strands harness](https://strandsagents.com/docs/user-guide/harness/)** agent (`backend/pix_agent.py`) whose model is a **LiteLLM** endpoint (OpenAI-compatible) using Anthropic models. The API key never reaches the browser.
- **Edit model**: Pix works with tools, like a coding agent, directly on the game folder: `read` / `write` / `edit` for `game.py` (built into the harness), plus our own `voir_ressources`, `modifier_ressources` and `tester_jeu`. Each turn it can make several tool calls (read the code, change it, test it, fix it), then writes a short kid-friendly explanation. When the turn ends the backend sends the new `game.py` and `res.pyxres` to the UI, which updates the editor and reloads the preview. The chat shows what Pix is doing ("Je lis ton code…", "Je teste le jeu…").
- The file tools are locked to the game's folder (`GameFolderSandbox`) and there is no shell. Pix's conversation (with its tool calls) is saved by the harness in `games/<name>/.pix/`, so it continues where it left off after a restart. Games made before this change start with their old chat as text.
- Kids can also edit the code directly; the code on screen is saved to `game.py` before each message, and Pix is told to read it first.
- **What changed**: in the Code tab a thin colored gutter marks the lines added (green), modified (yellow) or deleted (red) by the last commit, so the kid sees what Pix just did.
- **Git history**: each game folder is its own git repository (created when the game is created, or at the first message for older games). Before each Pix turn the kid's own changes are committed ("Modifications de l'élève"), then Pix's changes ("Pix : <message>"). `chat.json` is not versioned (Pix's memory in `.pix/` is). In the chat, **⏹ Arrêter** stops Pix mid-turn (what it already did is kept and committed), and **↩️ Annuler** on a kid's message puts the game (code, resources and Pix's memory) back to the version just before it and removes the rest of the chat. Undo is a new commit, so nothing is ever lost: `git log` in the game folder shows everything.
- **URL**: the open game is in the URL (`http://localhost:8080/snake/`), so refreshing or bookmarking lands on it (nginx and the Vite dev server fall back to the app for these paths).
- **Saved games**: the start screen lets kids create a new game or reopen an old one. Each game is a folder in `games/<name>/` containing `game.py` (also runnable with desktop Pyxel: `pyxel run games/<name>/game.py`), `chat.json` (the conversation), `meta.json`, and `res.pyxres` once the kid has drawn sprites. Changes are saved automatically. Set `GAMES_DIR` in `backend/.env` to store them elsewhere.
- **Sprites**: the 🎨 Sprites tab embeds Pyxel's official resource editor (images, tilemaps, sounds, music). Its 💾 save button writes `res.pyxres` into the game folder, and the preview loads it so the game can use `pyxel.load("res.pyxres")` and `pyxel.blt(...)`. **🔄 Recharger** reloads the saved file from disk into the editor and the preview.
- **Pix draws and composes too**: the `modifier_ressources` tool runs a small Python script with headless Pyxel on the server (`backend/res_tool.py`, 20 s limit, on a copy so a failing script leaves the file untouched and Pix gets the error to fix it). It draws sprites pixel by pixel, lays out tilemaps and writes sounds and music into `res.pyxres`, which the kid then tweaks in the Sprites tab. `voir_ressources` gives Pix a text description of the current file, so the kid's edits are kept. `tester_jeu` runs the game headless for 60 frames and returns any crash. This needs `pyxel` in the backend venv (`pip install -r requirements.txt`).
- **Language**: the UI and the tutor (Pix) are in French. The tutor prompt lives in `backend/prompt_fr.md`.

## Run it with Docker

```bash
cp backend/.env.example backend/.env   # fill in LITELLM_API_KEY and LITELLM_MODEL
docker compose up -d --build
```

Then open http://localhost:8080 (change it with `PORT=9000 docker compose up -d`).

- `frontend` = the built app served by nginx, which proxies `/api` to `backend` (streaming not buffered).
- `backend` = FastAPI + headless Pyxel. Games are stored in `./games` on your disk (mounted as a volume).
- LiteLLM is expected on the laptop: by default the backend calls `http://host.docker.internal:4001`. If LiteLLM runs elsewhere, set `LITELLM_BASE_URL` in your shell or in a `.env` file next to `docker-compose.yml` (e.g. `LITELLM_BASE_URL=http://host.docker.internal:4000`) (the `localhost` value in `backend/.env` is ignored by Docker, because `localhost` inside the container is the container itself).

## Run it without Docker (development)

### 1. Backend (AI proxy)
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in LITELLM_BASE_URL, LITELLM_API_KEY, LITELLM_MODEL
uvicorn app:app --reload --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to :8000
```

Open the browser, type *"Je veux créer un jeu de labyrinthe"*, and go.

## Tests

```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest -q
cd frontend && npm test
```

- Backend (`backend/tests/`): the real FastAPI app, Strands harness, git and headless Pyxel, with a scripted model in place of LiteLLM (no network, no API key). Covers saving/loading games, the chat stream and its commits, the folder sandbox, ⏹ stop, ↩️ undo, and `res_tool.py` (build, describe, check).
- Frontend (`frontend/src/*.test.ts`, Vitest): the change-gutter diff, the chat text cleanup and the SSE stream parser.

## Project layout
```
backend/
  app.py          API: games on disk, git history, chat stream (SSE), stop, undo
  pix_agent.py    the Pix agent: Strands harness, sandbox, resource and test tools
  res_tool.py     headless Pyxel: draw/compose into res.pyxres, describe it, test-run a game
  prompt_fr.md    the tutor prompt (French)
  tests/          pytest suite
frontend/src/
  App.tsx         game picker, URL routing, chat turn, undo
  ChatPane.tsx    the chat (stop / undo buttons)
  RightPane.tsx   Aperçu / Code / Sprites tabs
  changeGutter.ts the "what changed" gutter in the code editor
  pyxelFrame.ts   in-browser Pyxel (Pyodide) for the preview and the resource editor
  api.ts          backend calls and the SSE parser
games/            one folder (and git repo) per game, not versioned here
```
