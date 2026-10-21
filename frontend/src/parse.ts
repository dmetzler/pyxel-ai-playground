// Turns an assistant reply into what the chat bubble shows. Pix edits
// game.py and res.pyxres with tools, so replies are mostly prose; old replies
// saved before that still contain whole code blocks, which we hide (the code
// lives in the Code tab, the drawings in the Sprites tab).
import { Lang, MessageKey, translate } from "./i18n";

const FENCE = /```(?:python|py|ressources)?\s*\n([\s\S]*?)```/g;

// Small snippets Pix quotes to explain are kept; whole files are not.
const MAX_SHOWN_LINES = 12;

const TOOL_LABELS: Record<string, MessageKey> = {
  read: "tool.read",
  write: "tool.write",
  edit: "tool.edit",
  view_resources: "tool.view_resources",
  edit_resources: "tool.edit_resources",
  test_game: "tool.test_game",
};

export function chatText(text: string, activity: string | null, lang: Lang): {
  text: string;
  activity: string | null;
} {
  let out = text.replace(FENCE, (block, body: string) =>
    body.split("\n").length > MAX_SHOWN_LINES ? "" : block,
  );
  // Hide an unfinished code block while it is still streaming.
  const fences = out.match(/```/g)?.length ?? 0;
  if (fences % 2 === 1) out = out.slice(0, out.lastIndexOf("```"));
  return {
    text: out.trimEnd(),
    activity: activity ? translate(lang, TOOL_LABELS[activity] ?? "tool.default") : null,
  };
}
