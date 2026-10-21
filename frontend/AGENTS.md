# frontend/ — Vite + React 18 + TypeScript UI

## OVERVIEW
Single-page app in `src/` (no router lib, no state lib); Pyxel runs in sandboxed iframes via Pyodide from the jsDelivr CDN. Earned its file: distinct domain (UI, in-browser Pyxel, i18n).

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| App state, URL routing (`/<game-id>/`), chat turn, autosave, undo, export/PDF | `src/App.tsx` | the only stateful container |
| Start screen | `src/GamePicker.tsx` | create, open, delete (confirm, blocked while busy), import |
| Chat UI | `src/ChatPane.tsx` | stop + undo buttons |
| Preview / Code / Sprites tabs | `src/RightPane.tsx` | CodeMirror editor + two iframes |
| Iframe documents | `src/pyxelFrame.ts` | `buildPyxelDocument`, `buildEditorDocument`; `postMessage` types `pyxel-error`, `pyxres-saved` |
| Change gutter | `src/changeGutter.ts` | `diffLines(before, now)` vs `base_code` from backend |
| Backend calls + SSE parser | `src/api.ts` | `streamChat`, `apiFetch`, typed endpoint helpers |
| Chat text cleanup | `src/parse.ts` | `chatText(text, activity, lang)` |
| UI strings | `src/i18n.ts` | `fr` dict defines `MessageKey`; `useI18n()` -> `{lang, t}` |
| Starter game + welcome | `src/starter.ts` | one per language |

## CONVENTIONS
- Every backend call goes through `apiFetch` (adds `X-Lang`); exceptions are plain URLs (`exportUrl`, `storyPdfUrl`) used as links.
- `fr` is the source dictionary: `en`/`pl` are typed `Messages`, so a missing key is a type error and `i18n.test.ts` checks keys + non-empty values.
- Resources (`res.pyxres`) travel as base64 strings everywhere (API, state, iframe messages).
- Remounting is done with counters (`runId`, `editorVersion`) as React `key`s, not imperative reloads.
- Comments mix French and English; keep whatever the surrounding block uses.
- Tests are pure-logic Vitest files next to the source (`*.test.ts`); no DOM/component tests.

## ANTI-PATTERNS
- Starter code and any text drawn with `pyxel.text` must be ASCII (enforced by `i18n.test.ts`).
- Inject code/resources into iframe HTML only via `lit()` (JSON + `</` escaping); never string-concatenate raw code.
- Don't drop `sandbox="allow-scripts allow-same-origin"` or the `NO_FILES` root (`/api/no-files`): without it pyxel.js fetches missing files and gets Vite's `index.html`.
- Don't bypass the backend for persistence: the backend writes `game.py` from `current_code` at each turn; the UI only autosaves via `saveGame` / `saveResources`.

## COMMANDS
```bash
npm run dev     # :5173, proxies /api to $BACKEND_URL or :8000
npm test        # vitest run
npm run build   # tsc -b && vite build (CI runs it)
```
