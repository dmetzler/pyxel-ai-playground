import { useEffect, useMemo, useState } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { buildEditorDocument, buildPyxelDocument } from "./pyxelFrame";
import { changeGutter } from "./changeGutter";

export default function RightPane(props: {
  code: string;
  // game.py before the last commit; the editor marks what changed since.
  baseCode: string | null;
  resources: string | null;
  editorVersion: number;
  runId: number;
  gameError: string | null;
  onCodeChange: (code: string) => void;
  onRun: () => void;
  onAskFix: () => void;
  onReloadResources: () => Promise<void>;
}) {
  const [tab, setTab] = useState<"preview" | "code" | "sprites">("preview");
  // The editor is only started the first time the tab is opened, then kept
  // alive (hidden) so switching tabs doesn't lose the drawing in progress.
  const [editorOpened, setEditorOpened] = useState(false);
  const [editorDoc, setEditorDoc] = useState<string | null>(null);
  // Pix changed res.pyxres: reopen the editor on the new file.
  useEffect(() => {
    if (editorOpened) setEditorDoc(buildEditorDocument(props.resources));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.editorVersion]);
  // Only rebuild the game when runId changes, not on every keystroke.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const doc = useMemo(() => buildPyxelDocument(props.code, props.resources), [props.runId]);
  const extensions = useMemo(() => [python(), changeGutter(props.baseCode)], [props.baseCode]);

  return (
    <section className="pane right">
      <header className="pane-title tabs">
        <button className={tab === "preview" ? "active" : ""} onClick={() => setTab("preview")}>
          🎮 Aperçu
        </button>
        <button className={tab === "code" ? "active" : ""} onClick={() => setTab("code")}>
          📝 Code
        </button>
        <button
          className={tab === "sprites" ? "active" : ""}
          onClick={() => {
            setTab("sprites");
            if (!editorOpened) {
              setEditorOpened(true);
              setEditorDoc(buildEditorDocument(props.resources));
            }
          }}
        >
          🎨 Sprites
        </button>
        <span className="spacer" />
        <button
          className="run"
          onClick={() => {
            props.onRun();
            setTab("preview");
          }}
        >
          ▶ Lancer
        </button>
      </header>
      <div className="right-body">
        <div className="preview" style={{ display: tab === "preview" ? "flex" : "none" }}>
          <iframe
            key={props.runId}
            title="Jeu Pyxel"
            srcDoc={doc}
            sandbox="allow-scripts allow-same-origin"
            allow="autoplay; gamepad"
          />
          <p className="hint">Clique sur le jeu, puis utilise le clavier pour jouer !</p>
        </div>
        <div className="code" style={{ display: tab === "code" ? "block" : "none" }}>
          <p className="hint">
            Voici le vrai code de ton jeu. Tu peux le modifier, puis appuyer sur ▶ Lancer. Pix verra tes changements !
            <span className="legend">
              <i className="added" /> ajouté <i className="changed" /> modifié <i className="deleted" /> effacé (au dernier changement)
            </span>
          </p>
          <CodeMirror
            value={props.code}
            height="100%"
            theme="dark"
            extensions={extensions}
            onChange={props.onCodeChange}
          />
        </div>
        <div className="sprites" style={{ display: tab === "sprites" ? "flex" : "none" }}>
          <p className="hint">
            Dessine ou modifie tes personnages, décors et musiques ici (Pix peut aussi en créer pour toi). Clique sur
            la 💾 disquette en haut de l'éditeur pour enregistrer, sinon tes changements seront perdus !
            <button
              className="reload"
              title="Recharger les dessins et les sons enregistrés (ce qui n'est pas enregistré sera perdu)"
              onClick={() => props.onReloadResources()}
            >
              🔄 Recharger
            </button>
          </p>
          {editorDoc && (
            <iframe key={props.editorVersion} title="Éditeur de sprites Pyxel" srcDoc={editorDoc} sandbox="allow-scripts allow-same-origin" />
          )}
        </div>
        {props.gameError && tab !== "sprites" && (
          <div className="game-error">
            <strong>🐞 Ton jeu a un bug.</strong>
            <pre>{props.gameError}</pre>
            <button onClick={props.onAskFix}>Demander à Pix de le réparer</button>
          </div>
        )}
      </div>
    </section>
  );
}
