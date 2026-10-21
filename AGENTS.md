# PROJECT KNOWLEDGE BASE

**Generated:** 2026-10-21
**Commit:** 4a44e2a
**Branch:** main

## OVERVIEW
Classroom tool: kids build Pyxel retro games by chatting with Pix, a Strands-harness coding agent. FastAPI backend (agent, git-per-game, PDF story) + Vite/React frontend running Pyxel in-browser via Pyodide.

## STRUCTURE
```
pyxel-ai-playground/
├── backend/        # FastAPI app, Pix agent, headless Pyxel tool, PDF story -> backend/AGENTS.md
├── frontend/       # React UI, in-browser Pyxel iframes, i18n -> frontend/AGENTS.md
├── charts/pyxel-ai-playground/  # Helm chart: frontend pod = oauth2-proxy sidecar + nginx; backend single replica on RWO PVC
├── games/          # runtime data: one folder + git repo per game (gitignored, kids' work)
├── docs/images/    # README screenshot only
├── .github/workflows/  # ci.yml (pytest, vitest+build, helm lint), images.yml (ghcr multi-arch)
└── docker-compose.yml  # backend + nginx frontend on :8080
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| API route / game storage / undo / import | `backend/app.py` | |
| Change what Pix can do | `backend/pix_agent.py`, `backend/prompt_*.md` | tools + sandbox; three prompts |
| Sprite/sound/test-run logic | `backend/res_tool.py` | always run as subprocess |
| PDF booklet | `backend/story.py` | WeasyPrint, needs Pango |
| UI behavior | `frontend/src/App.tsx` | single state container |
| Add a language | `frontend/src/i18n.ts`, `frontend/src/starter.ts`, `backend/prompt_<lang>.md`, `backend/i18n.py` | also `LANGS` in both i18n files and `GameCreate.lang` Literal in `app.py` |
| nginx proxy settings | `frontend/nginx.conf` AND `charts/.../templates/nginx-configmap.yaml` | duplicated: change both |
| Deploy values | `charts/pyxel-ai-playground/values.yaml` | |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `chat` | route | `backend/app.py` | SSE turn: commit student, stream agent, commit Pix |
| `undo` | route | `backend/app.py` | restore commit as new commit |
| `import_game` / `_zip_members` | route/guard | `backend/app.py` | safe zip import |
| `make_agent` | fn | `backend/pix_agent.py` | harness + tools + `GameFolderSandbox` |
| `run_res_tool` | fn | `backend/pix_agent.py` | subprocess wrapper, 20 s timeout |
| `check` / `describe` / `build` | fn | `backend/res_tool.py` | headless Pyxel ops |
| `build_story_pdf` | fn | `backend/story.py` | PDF story |
| `streamChat` | fn | `frontend/src/api.ts` | SSE client |
| `buildPyxelDocument` | fn | `frontend/src/pyxelFrame.ts` | preview iframe HTML |

## CONVENTIONS
- Languages: `fr`, `en`, `pl`; `fr` is the default and fallback everywhere. A game's language is fixed in `meta.json`; UI language travels as `X-Lang` header.
- Game folder layout: `game.py`, `meta.json`, `chat.json` (not versioned), `res.pyxres`, `.pix/` (agent session, versioned), `.gitignore`.
- Game ids are slugs (`^[a-z0-9][a-z0-9-]{0,63}$`); URL is `/<id>/`.
- User-facing and agent-facing strings are often French in code; that is intended (primary audience).
- Config via env only: `LITELLM_BASE_URL`, `LITELLM_API_KEY`, `LITELLM_MODEL`, `PIX_MAX_TOKENS`, `GAMES_DIR`. LLM is any OpenAI-compatible endpoint.

## ANTI-PATTERNS (THIS PROJECT)
- Never commit `games/`, `backend/.env` or `.env`; never let the API key reach the frontend.
- Don't run more than one backend replica: per-game locks and live agents are in-process memory, storage is RWO.
- Don't buffer `/api/` in any proxy (SSE) and keep `client_max_body_size` >= backend import limit (50 MB zip, base64 resources).
- Don't add sound output to server-side Pyxel: `res_tool.py` forces `SDL_AUDIODRIVER=dummy` because headless hosts print audio errors into tool output.

## COMMANDS
```bash
docker compose up -d --build                         # full app on :8080 (needs backend/.env)
cd backend && uvicorn app:app --reload --port 8000   # dev backend
cd frontend && npm run dev                           # dev UI :5173
cd backend && python -m pytest -q                    # backend tests (scripted model, no network)
cd frontend && npm test && npm run build
helm lint charts/pyxel-ai-playground --set oauth2Proxy.clientId=x --set oauth2Proxy.clientSecret=y \
  --set oauth2Proxy.cookieSecret=0123456789abcdef0123456789abcdef --set oauth2Proxy.issuerUrl=https://idp.example.com --set openai.apiKey=k
```

## NOTES
- CI needs a global git identity (games are git repos) and `libpango` for WeasyPrint.
- In Docker, `localhost` in `backend/.env` is ignored for the LLM; compose defaults to `host.docker.internal:4001`.
- Pyxel web runtime loads from jsDelivr CDN: preview needs internet.
- `backend/Dockerfile` copies modules by name; new `.py` files must be added there.
