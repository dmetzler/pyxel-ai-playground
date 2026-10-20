import { RangeSet, StateField } from "@codemirror/state";
import { EditorView, GutterMarker, gutter } from "@codemirror/view";

type Change = "added" | "changed" | "deleted";

class ChangeMarker extends GutterMarker {
  constructor(readonly kind: Change) {
    super();
  }
  eq(other: ChangeMarker) {
    return other.kind === this.kind;
  }
  toDOM() {
    const el = document.createElement("div");
    el.className = `cm-change cm-change-${this.kind}`;
    return el;
  }
}

const MARKERS = { added: new ChangeMarker("added"), changed: new ChangeMarker("changed"), deleted: new ChangeMarker("deleted") };

// Above this size the O(n*m) line diff gets slow; kids' games stay far below.
const MAX_LINES = 3000;

/** For each line of `now` (0-based), how it differs from `before`. */
export function diffLines(before: string, now: string): Map<number, Change> {
  const a = before.split("\n");
  const b = now.split("\n");
  const out = new Map<number, Change>();
  if (a.length > MAX_LINES || b.length > MAX_LINES) return out;
  // Longest common subsequence table, filled from the end.
  const lcs = Array.from({ length: a.length + 1 }, () => new Uint16Array(b.length + 1));
  for (let i = a.length - 1; i >= 0; i--)
    for (let j = b.length - 1; j >= 0; j--)
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) {
      i++;
      j++;
      continue;
    }
    // A run of removed and/or inserted lines between two common lines.
    let removed = 0;
    const start = j;
    while (i < a.length || j < b.length) {
      if (i < a.length && j < b.length && a[i] === b[j]) break;
      if (j >= b.length || (i < a.length && lcs[i + 1][j] >= lcs[i][j + 1])) {
        i++;
        removed++;
      } else j++;
    }
    for (let k = start; k < j; k++) out.set(k, removed > 0 ? "changed" : "added");
    if (j === start && removed > 0) out.set(Math.min(start, b.length - 1), "deleted");
  }
  return out;
}

/** A thin gutter coloring the lines that differ from `base` (the previous version). */
export function changeGutter(base: string | null) {
  const changes = StateField.define<RangeSet<GutterMarker>>({
    create: (state) => markers(state.doc.toString()),
    update: (value, tr) => (tr.docChanged ? markers(tr.state.doc.toString()) : value),
  });
  function markers(doc: string) {
    if (base === null) return RangeSet.empty;
    const lines = doc.split("\n");
    let pos = 0;
    const starts = lines.map((l) => {
      const p = pos;
      pos += l.length + 1;
      return p;
    });
    const ranges = [...diffLines(base, doc)].sort(([x], [y]) => x - y).map(([line, kind]) => MARKERS[kind].range(starts[line]));
    return RangeSet.of(ranges);
  }
  return [
    changes,
    gutter({ class: "cm-change-gutter", markers: (view) => view.state.field(changes) }),
    EditorView.theme({
      ".cm-change-gutter": { width: "4px", minWidth: "4px" },
      ".cm-change-gutter .cm-gutterElement": { padding: "0" },
      ".cm-change": { width: "4px", height: "100%" },
      ".cm-change-added": { background: "#06d6a0" },
      ".cm-change-changed": { background: "#ffd166" },
      ".cm-change-deleted": { borderTop: "3px solid #ef476f", height: "0" },
    }),
  ];
}
