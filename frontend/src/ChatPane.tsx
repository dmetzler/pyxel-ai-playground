import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useI18n } from "./i18n";

interface Bubble {
  role: "user" | "assistant";
  text: string;
  activity: string | null;
  canUndo: boolean;
}

const IDEAS = ["chat.idea1", "chat.idea2", "chat.idea3"] as const;

export default function ChatPane(props: {
  messages: Bubble[];
  busy: boolean;
  error: string | null;
  onSend: (text: string) => void;
  onStop: () => void;
  onUndo: (index: number) => void;
}) {
  const { t } = useI18n();
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [props.messages]);

  const submit = (text: string) => {
    if (!text.trim() || props.busy) return;
    props.onSend(text);
    setInput("");
  };

  return (
    <section className="pane chat">
      <header className="pane-title">{t("chat.title")}</header>
      <div className="messages">
        {props.messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.text ? <ReactMarkdown>{m.text}</ReactMarkdown> : null}
            {m.activity && <div className="building">{m.activity}</div>}
            {!m.text && !m.activity && props.busy && <div className="building">{t("chat.thinking")}</div>}
            {m.canUndo && (
              <button className="undo" title={t("chat.undoTitle")} onClick={() => props.onUndo(i)}>
                {t("chat.undo")}
              </button>
            )}
          </div>
        ))}
        {props.messages.length === 1 && (
          <div className="ideas">
            {IDEAS.map((key) => (
              <button key={key} onClick={() => submit(t(key))}>{t(key)}</button>
            ))}
          </div>
        )}
        {props.error && <div className="error">{t("chat.error", { error: props.error })}</div>}
        <div ref={endRef} />
      </div>
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
      >
        <textarea
          value={input}
          placeholder={t("chat.placeholder")}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(input);
            }
          }}
          rows={2}
        />
        {props.busy ? (
          <button type="button" className="stop" onClick={props.onStop}>{t("chat.stop")}</button>
        ) : (
          <button type="submit" disabled={!input.trim()}>{t("chat.send")}</button>
        )}
      </form>
    </section>
  );
}
