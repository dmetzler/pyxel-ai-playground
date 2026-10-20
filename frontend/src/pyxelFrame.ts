// Builds the HTML documents for the sandboxed iframes. They load the official
// Pyxel web runtime (Pyodide + Pyxel wheel) from the CDN. Python errors and
// saved resource files are posted back to the parent window.

const PYXEL_JS = "https://cdn.jsdelivr.net/gh/kitao/pyxel/wasm/pyxel.js";
export const RES_FILE = "res.pyxres";
// pyxel.js fetches files the game opens that don't exist yet from "root"; send
// those to a URL that 404s so Vite's index.html fallback is never copied in.
const NO_FILES = JSON.stringify("/api/no-files");

// JSON gives a string literal valid in both JS and Python; escape "</" so the
// content can't close the <script> tag.
const lit = (s: string) => JSON.stringify(s).replace(/<\//g, "<\\/");

function page(launch: string): string {
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>html,body{margin:0;height:100%;background:#1d1d2b;overflow:hidden}</style>
<script>
  const origError = console.error.bind(console);
  console.error = (...args) => {
    origError(...args);
    const msg = args.map(String).join(" ");
    if (msg.includes("Traceback") || msg.includes("Error")) {
      parent.postMessage({ type: "pyxel-error", message: msg }, "*");
    }
  };
  window.addEventListener("error", (e) => {
    parent.postMessage({ type: "pyxel-error", message: String(e.message) }, "*");
  });
  // pyxel.save() in the browser normally downloads the file; send it to the
  // app instead so it is stored in the game's folder. pyxel.js assigns this
  // global during startup, so make that assignment a no-op.
  const saveToApp = (filename) => {
    const bytes = window.pyxelContext.pyodide.FS.readFile(filename);
    let bin = "";
    for (const b of bytes) bin += String.fromCharCode(b);
    parent.postMessage({ type: "pyxres-saved", data: btoa(bin) }, "*");
  };
  Object.defineProperty(window, "_savePyxelFile", { get: () => saveToApp, set: () => {} });
</script>
<script src="${PYXEL_JS}"></script>
</head>
<body>
<script>${launch}</script>
</body>
</html>`;
}

/** Run the kid's game, with their sprite file (base64) if they have one. */
export function buildPyxelDocument(code: string, resources: string | null): string {
  // Write res.pyxres next to the game, then run the code as "game.py" so error
  // line numbers match the editor.
  const script = [
    "import base64",
    resources ? `open(${lit(RES_FILE)}, "wb").write(base64.b64decode(${lit(resources)}))` : "",
    `exec(compile(${lit(code)}, "game.py", "exec"), {"__name__": "__main__"})`,
  ].join("\n");
  return page(`launchPyxel({ command: "run", root: ${NO_FILES}, script: ${lit(script)} });`);
}

/** Open Pyxel's resource editor (sprites, tilemaps, sounds, music). */
export function buildEditorDocument(resources: string | null): string {
  return page(
    `launchPyxel({ command: "edit", root: ${NO_FILES}, name: ${lit(RES_FILE)}, editor: "image"${resources ? `, base64: ${lit(resources)}` : ""} });`,
  );
}
