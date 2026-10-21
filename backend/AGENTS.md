# backend/ — FastAPI + Pix agent + headless Pyxel

## OVERVIEW
Flat Python module set (no package, no `__init__.py`): `uvicorn app:app` from inside `backend/`. Earned its file: distinct domain (agent, git-per-game, PDF, sandbox).

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| HTTP routes, game storage, git, SSE chat, undo, import/export | `app.py` | all `@app.*` routes; `_git`, `_commit`, `_ensure_repo`, `_game_dir` |
| Agent wiring, tools, sandbox | `pix_agent.py` | `make_agent`, `make_model`, `_game_tools`, `GameFolderSandbox` |
| Headless Pyxel subprocess (build/describe/check) | `res_tool.py` | CLI: `build <res> <script>`, `describe <res>`, `check <game.py>` |
| PDF story | `story.py` | `build_story_pdf(d)`; screenshots via `res_tool.py check` per commit |
| Backend strings, `X-Lang` | `i18n.py` | `t(lang, key)` = game lang; `tr(key)` = request lang |
| Tutor prompt | `prompt_{fr,en,pl}.md` | keep the three in sync; fr is the fallback |
| Test harness | `tests/conftest.py` | `ScriptedModel`, fixtures `games_dir`, `client`, `script`, `game` |

## CONVENTIONS
- Two languages per request: `t(_game_lang(d), ...)` for anything persisted (commits, Pix prompt, PDF); `tr(...)` for HTTP error details (UI language from `X-Lang`, set by `LangMiddleware` contextvar).
- One live agent per game in `_agents`, one turn at a time via `_locks[game_id]`. Anything that mutates the game folder (undo, delete) must check/hold that lock; return 409 `pix_busy` when locked.
- Drop `_agents[game_id]` whenever `.pix/` changes on disk (undo, agent error) so the harness reloads its session.
- Git always through `_git(d, ...)` (injects Pix identity + `safe.directory=*`). `_commit` is a no-op when the tree is clean and returns HEAD.
- Chat turn order is load-bearing: write `current_code` -> commit student edits (`before`) -> agent stream -> commit Pix -> append `chat.json` -> final `done` SSE event with `code`, `base_code`, `resources`, `resources_changed`.
- Undo never rewrites history: `read-tree -u --reset <commit>` + `clean -fd` + new commit.
- Agent tools return French/plain strings to the model and never raise; failures come back as `ERREUR ...` / `LE JEU PLANTE ...` text so Pix can fix them.
- Heavy Pyxel work always runs in a subprocess via `run_res_tool` (20 s timeout); never `import pyxel` in the API process. `edit_resources` works on a temp copy and only writes back on success.
- `story` is imported lazily inside the route (WeasyPrint/Pango is heavy and optional in dev).
- SSE frames: `_sse({...})` -> `data: <json>\n\n`; event keys `delta`, `tool`, `error`, `done`.

## ANTI-PATTERNS
- NEVER build a game path without `_game_dir()` (regex `GAME_ID_RE` is the traversal guard) or call `agent.cancel()` when the lock is free (Strands keeps the flag and kills the next turn).
- NEVER give Pix a shell: `GameFolderSandbox.execute_*` must keep raising; `.pix/` stays off-limits to file tools.
- NEVER loosen `_zip_members` (absolute paths, `..`, drive colons, symlinks, size caps) or skip dropping imported `.git/hooks` and rewriting `.git/config`.
- Don't version `chat.json` (`GAME_GITIGNORE`); `.pix/` IS versioned so undo restores Pix's memory.
- New backend module? Add it to the `COPY` line in `Dockerfile` (files are listed explicitly).
- Tests must not hit a real LLM: use the `script` fixture; everything else (git, harness, headless Pyxel) stays real. Gate mid-turn behavior with `ScriptedModel.gates`/`started` events, not sleeps.

## COMMANDS
```bash
python -m pytest -q                       # from backend/, needs git identity + Pango
python -m pytest -q tests/test_chat.py -k stop
python res_tool.py check ../games/snake/game.py
```
