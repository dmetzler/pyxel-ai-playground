import { useCallback, useEffect, useRef, useState } from "react";
import { ChatMessage, ChatResult, createGame, loadGame, saveGame, saveResources, stopChat, streamChat, undoTo } from "./api";
import { chatText } from "./parse";
import { STARTER_CODE, WELCOME_MESSAGE } from "./starter";
import ChatPane from "./ChatPane";
import GamePicker from "./GamePicker";
import RightPane from "./RightPane";

interface OpenGame {
  id: string;
  name: string;
}

export default function App() {
  const [game, setGame] = useState<OpenGame | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [code, setCode] = useState(STARTER_CODE);
  // game.py before the last commit, to color what it changed in the editor.
  const [baseCode, setBaseCode] = useState<string | null>(null);
  // The game's res.pyxres (sprites, tilemaps, sounds) as base64, or null.
  const [resources, setResources] = useState<string | null>(null);
  // Bumped to reload the Sprites editor after Pix changed res.pyxres.
  const [editorVersion, setEditorVersion] = useState(0);
  // Bumped to restart the preview with the current code.
  const [runId, setRunId] = useState(0);
  const [busy, setBusy] = useState(false);
  // What Pix is doing right now (tool name), shown under its bubble.
  const [activity, setActivity] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gameError, setGameError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"saved" | "saving" | "error">("saved");
  const codeRef = useRef(code);
  codeRef.current = code;
  const gameIdRef = useRef<string | null>(null);
  gameIdRef.current = game?.id ?? null;

  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      if (e.data?.type === "pyxel-error") setGameError(e.data.message);
      if (e.data?.type === "pyxres-saved") {
        setResources(e.data.data);
        setRunId((n) => n + 1);
        const id = gameIdRef.current;
        if (id) {
          setSaveState("saving");
          saveResources(id, e.data.data).then(
            () => setSaveState("saved"),
            () => setSaveState("error"),
          );
        }
      }
    };
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, []);

  // Autosave to games/<id>/ on disk shortly after any change, but not while
  // Pix is still streaming a reply.
  useEffect(() => {
    if (!game || busy) return;
    setSaveState("saving");
    const t = setTimeout(() => {
      saveGame(game.id, code, messages).then(
        () => setSaveState("saved"),
        () => setSaveState("error"),
      );
    }, 800);
    return () => clearTimeout(t);
  }, [game, code, messages, busy]);

  const open = (g: OpenGame, c: string, ms: ChatMessage[], res: string | null, base: string | null = null) => {
    setGame(g);
    setBaseCode(base);
    setResources(res);
    setCode(c);
    setMessages(ms);
    setError(null);
    setGameError(null);
    setRunId((n) => n + 1);
    setEditorVersion((n) => n + 1);
  };

  // The open game is in the URL (/snake/), so a refresh or a bookmark lands on it.
  const showGame = (id: string | null) => {
    const path = id ? `/${id}/` : "/";
    if (location.pathname !== path) history.pushState(null, "", path);
  };

  const openFromUrl = useCallback(async () => {
    const id = location.pathname.split("/").filter(Boolean)[0];
    if (!id) {
      setGame(null);
      return;
    }
    try {
      const g = await loadGame(decodeURIComponent(id));
      open(g, g.code, g.messages, g.resources, g.base_code);
    } catch {
      history.replaceState(null, "", "/");
      setGame(null);
    }
  }, []);

  useEffect(() => {
    openFromUrl();
    window.addEventListener("popstate", openFromUrl);
    return () => window.removeEventListener("popstate", openFromUrl);
  }, [openFromUrl]);

  const onCreate = async (name: string) => {
    const welcome: ChatMessage[] = [{ role: "assistant", content: WELCOME_MESSAGE }];
    const g = await createGame(name, STARTER_CODE, welcome);
    open(g, STARTER_CODE, welcome, null);
    showGame(g.id);
  };

  const onOpen = async (id: string) => {
    const g = await loadGame(id);
    open(g, g.code, g.messages, g.resources, g.base_code);
    showGame(id);
  };

  // Reload res.pyxres from disk (Pix or another window may have changed it).
  const reloadResources = async () => {
    if (!game) return;
    const g = await loadGame(game.id);
    setResources(g.resources);
    setEditorVersion((n) => n + 1);
    setRunId((n) => n + 1);
  };

  const stop = () => {
    if (game) stopChat(game.id).catch((e) => setError(String(e)));
  };

  // Undo message i (a kid's message) and everything after it.
  const undo = async (i: number) => {
    const commit = messages[i]?.commit;
    if (!game || busy || !commit) return;
    if (!confirm("Annuler ce message ? Le jeu reviendra comme il était juste avant, et la suite de la discussion sera effacée.")) return;
    try {
      const r = await undoTo(game.id, commit);
      setMessages(messages.slice(0, i));
      setCode(r.code);
      setBaseCode(r.base_code);
      setResources(r.resources);
      setGameError(null);
      setError(null);
      setRunId((n) => n + 1);
      setEditorVersion((n) => n + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const send = useCallback(
    async (text: string) => {
      if (busy || !text.trim()) return;
      setError(null);
      const history = [...messages, { role: "user" as const, content: text }];
      setMessages([...history, { role: "assistant", content: "" }]);
      setBusy(true);
      let reply = "";
      const apply = (r: ChatResult) => {
        // Remember the version before this turn on the kid's message, to undo it.
        setMessages((ms) =>
          ms.map((m, i) => (i === history.length - 1 ? { ...m, commit: r.commit } : m)),
        );
        if (r.resourcesChanged) {
          setResources(r.resources);
          setEditorVersion((n) => n + 1);
        }
        setBaseCode(r.baseCode);
        if (r.code !== codeRef.current || r.resourcesChanged) {
          setCode(r.code);
          setGameError(null);
          setRunId((n) => n + 1);
        }
      };
      try {
        apply(
          await streamChat(
            gameIdRef.current!,
            text,
            codeRef.current,
            // Skip the canned welcome. Only used if Pix has no saved session yet.
            messages.slice(1),
            (delta) => {
              reply += delta;
              setActivity(null);
              setMessages((ms) => [...ms.slice(0, -1), { role: "assistant", content: reply }]);
            },
            (tool) => {
              // Text before a tool call and after it are separate sentences.
              if (reply && !reply.endsWith("\n")) reply += "\n\n";
              setActivity(tool);
            },
          ),
        );
      } catch (e) {
        const partial = (e as { result?: ChatResult }).result;
        if (partial) apply(partial);
        setError(e instanceof Error ? e.message : String(e));
        setMessages((ms) => (reply ? ms : ms.slice(0, -1)));
      } finally {
        setActivity(null);
        setBusy(false);
      }
    },
    [busy, messages],
  );

  if (!game) return <GamePicker onOpen={onOpen} onCreate={onCreate} />;

  const askToFix = () => {
    if (!gameError) return;
    send(
      "Mon jeu affiche cette erreur, tu peux m'aider à la réparer ?\n\n" +
        gameError.slice(0, 1500),
    );
  };

  return (
    <div className="shell">
      <div className="topbar">
        <button disabled={busy} onClick={() => { setGame(null); showGame(null); }}>📂 Mes jeux</button>
        <strong>{game.name}</strong>
        <span className={`save ${saveState}`}>
          {saveState === "saved" ? "✔ Sauvegardé" : saveState === "saving" ? "Sauvegarde…" : "⚠ Pas sauvegardé"}
        </span>
      </div>
      <div className="app">
        <ChatPane
          messages={messages.map((m, i) => ({
            role: m.role,
            ...(m.role === "assistant"
              ? chatText(m.content, busy && i === messages.length - 1 ? activity : null)
              : { text: m.content, activity: null }),
            canUndo: m.role === "user" && !!m.commit && !busy,
          }))}
          busy={busy}
          error={error}
          onSend={send}
          onStop={stop}
          onUndo={undo}
        />
        <RightPane
          key={game.id}
          code={code}
          baseCode={baseCode}
          resources={resources}
          editorVersion={editorVersion}
          runId={runId}
          gameError={gameError}
          onCodeChange={setCode}
          onRun={() => {
            setGameError(null);
            setRunId((n) => n + 1);
          }}
          onAskFix={askToFix}
          onReloadResources={reloadResources}
        />
      </div>
    </div>
  );
}
