// Turns an assistant reply into what the chat bubble shows. Pix edits
// game.py and res.pyxres with tools, so replies are mostly prose; old replies
// saved before that still contain whole code blocks, which we hide (the code
// lives in the Code tab, the drawings in the Sprites tab).

const FENCE = /```(?:python|py|ressources)?\s*\n([\s\S]*?)```/g;

// Small snippets Pix quotes to explain are kept; whole files are not.
const MAX_SHOWN_LINES = 12;

const TOOL_LABELS: Record<string, string> = {
  read: "📖 Je lis ton code…",
  write: "✍️ J'écris le code…",
  edit: "✍️ Je modifie le code…",
  voir_ressources: "🎨 Je regarde tes dessins et tes sons…",
  modifier_ressources: "🎨 Je dessine et je compose…",
  tester_jeu: "🧪 Je teste le jeu…",
};

export function chatText(text: string, activity: string | null): {
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
    activity: activity ? (TOOL_LABELS[activity] ?? "🛠️ Je travaille…") : null,
  };
}
