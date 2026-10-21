"""The story of a game, as a PDF the kid takes home.

build_story_pdf(game folder) -> PDF bytes: a cover with screenshots, one page per
step (what the kid asked, what Pix explained, the game after the step, the code
that changed), the full final code, and how to keep playing at home.
"""

import base64
import datetime
import difflib
import html
import json
import re
import subprocess
import sys
import tempfile
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import markdown
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name
from weasyprint import HTML

import i18n
from i18n import t

HERE = Path(__file__).parent
RES_TOOL = HERE / "res_tool.py"
APP_SHOT = HERE / "assets" / "app.png"

EXTRACT_MAX = 30  # lines of code shown per step
LONG_BLOCK = 12  # fenced code blocks in Pix's answers longer than this are dropped
# Emoji have no glyph in the PDF fonts: they would print as empty boxes.
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]+ ?")
FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
# ```python x = 1``` written on one line: markdown would show the word "python".
INLINE_FENCE_RE = re.compile(r"```(?:python|py)?[ \t]+([^\n`]+?)[ \t]*```")
# Fences indented inside a list item: the markdown fenced_code extension misses them.
INDENTED_FENCE_RE = re.compile(r"^([ \t]+)(```[^\n]*\n.*?^[ \t]*```)", re.S | re.M)
STYLE = get_style_by_name("friendly")


# --- Reading the game's history --------------------------------------------


def _git(d: Path, *args: str) -> str | None:
    p = subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=d,
                       capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def _show(d: Path, commit: str, path: str) -> bytes | None:
    p = subprocess.run(["git", "-c", "safe.directory=*", "show", f"{commit}:{path}"],
                       cwd=d, capture_output=True)
    return p.stdout if p.returncode == 0 else None


def _steps(d: Path, messages: list[dict]) -> list[dict]:
    """One step per kid message: request, Pix's answer, commits before and after."""
    head = (_git(d, "rev-parse", "HEAD") or "").strip() or None
    steps: list[dict] = []
    for m in messages:
        if m.get("role") == "user":
            steps.append({"ask": m.get("content", ""), "answer": [], "before": m.get("commit")})
        elif steps:
            steps[-1]["answer"].append(m.get("content", ""))
    for i, s in enumerate(steps):
        nxt = next((t["before"] for t in steps[i + 1:] if t["before"]), None)
        s["after"] = nxt or head
        if not s["before"] and i:
            s["before"] = steps[i - 1]["after"]
    return steps


# --- Screenshots -------------------------------------------------------------


def _screenshot(d: Path, commit: str | None) -> str | None:
    """The game at that commit after a few frames, as a data: URI (None if it crashes)."""
    if commit is None:
        return None
    code = _show(d, commit, "game.py")
    if code is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "game.py").write_bytes(code)
        res = _show(d, commit, "res.pyxres")
        if res is not None:
            (t / "res.pyxres").write_bytes(res)
        try:
            subprocess.run([sys.executable, str(RES_TOOL), "screenshot", str(t / "game.py"),
                            str(t / "shot.png"), "30"], cwd=t, capture_output=True, timeout=20)
        except subprocess.TimeoutExpired:
            return None
        shot = t / "shot.png"
        return _data_uri(shot.read_bytes()) if shot.is_file() else None


def _data_uri(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode()


def _figure(uri: str | None, caption: str, cls: str = "shot", lang: str = i18n.DEFAULT_LANG) -> str:
    if uri is None:
        img = f'<div class="noshot">{html.escape(t(lang, "story_noshot"))}</div>'
    else:
        img = f'<img class="{cls}" src="{uri}">'
    return f'<figure>{img}<figcaption>{html.escape(caption)}</figcaption></figure>'


# --- Code --------------------------------------------------------------------


def _token_style(ttype) -> str:
    s = STYLE.style_for_token(ttype)
    css = []
    if s["color"]:
        css.append(f"color:#{s['color']}")
    if s["bold"]:
        css.append("font-weight:bold")
    if s["italic"]:
        css.append("font-style:italic")
    return ";".join(css)


def _highlight_lines(code: str) -> list[str]:
    """Syntax-highlighted HTML, one string per source line."""
    lines, cur = [], []
    for ttype, value in PythonLexer(stripnl=False, ensurenl=False).get_tokens(code):
        parts = value.split("\n")
        for k, part in enumerate(parts):
            if k:
                lines.append("".join(cur))
                cur = []
            if part:
                style = _token_style(ttype)
                text = html.escape(part)
                cur.append(f'<span style="{style}">{text}</span>' if style else text)
    lines.append("".join(cur))
    n = len(code.split("\n"))
    return lines[:n]


def _code_table(rows: list[tuple[int | None, str, bool]], cls: str = "code") -> str:
    """rows: (line number or None for a gap, html, highlighted?)."""
    out = [f'<table class="{cls}">']
    for num, src, added in rows:
        if num is None:
            out.append('<tr class="gap"><td class="ln"></td><td class="src">…</td></tr>')
        else:
            cls = ' class="add"' if added else ""
            out.append(f'<tr{cls}><td class="ln">{num}</td><td class="src">{src or " "}</td></tr>')
    out.append("</table>")
    return "".join(out)


def _code_block(title: str, rows: list, cls: str = "code", legend: bool = False,
                lang: str = i18n.DEFAULT_LANG) -> str:
    """Title and the first lines kept together, so a page never ends on a lonely title."""
    head, rest = rows[:8], rows[8:]
    out = f'<div class="keep">{title}'
    if legend:
        out += f'<div class="legend"><span class="box"></span> {t(lang, "story_legend")}</div>'
    out += _code_table(head, cls) + "</div>"
    if rest:
        out += _code_table(rest, cls + " cont")
    return out


def _changed_lines(before: str, after: str) -> set[int]:
    """0-based indexes of lines of `after` that are new or changed."""
    changed: set[int] = set()
    sm = difflib.SequenceMatcher(None, before.split("\n"), after.split("\n"), autojunk=False)
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "insert"):
            changed.update(range(j1, j2))
    return changed


def _extract(before: str, after: str) -> list | None:
    """The changed part of the code, with a little context, at most EXTRACT_MAX lines."""
    changed = _changed_lines(before, after)
    if not changed:
        return None
    lines = _highlight_lines(after)
    shown: list[int] = []
    for i in sorted(changed):
        for j in range(max(0, i - 2), min(len(lines), i + 3)):
            if j not in shown and (not shown or j > shown[-1]):
                shown.append(j)
    rows: list[tuple[int | None, str, bool]] = []
    prev = -1
    for j in shown:
        if len([r for r in rows if r[0] is not None]) >= EXTRACT_MAX:
            rows.append((None, "", False))
            break
        if prev >= 0 and j != prev + 1:
            rows.append((None, "", False))
        rows.append((j + 1, lines[j], j in changed))
        prev = j
    if rows and rows[0][0] != 1 and rows[0][0] is not None:
        rows.insert(0, (None, "", False))
    return rows


# --- Text --------------------------------------------------------------------


def _clean(text: str) -> str:
    return EMOJI_RE.sub("", text)


def _answer_html(parts: list[str], lang: str = i18n.DEFAULT_LANG) -> str:
    def drop_long(m: re.Match) -> str:
        return "" if m.group(1).count("\n") > LONG_BLOCK else m.group(0)

    text = "\n\n".join(_clean(p) for p in parts)
    text = INDENTED_FENCE_RE.sub(lambda m: "\n" + textwrap.dedent(m.group(1) + m.group(2)) + "\n", text)
    text = FENCE_RE.sub(drop_long, text).strip()
    text = INLINE_FENCE_RE.sub(r"`\1`", text)
    if not text:
        return f"<p><em>{html.escape(t(lang, 'story_no_answer'))}</em></p>"
    return markdown.markdown(text, extensions=["fenced_code", "sane_lists"])




# --- The document ------------------------------------------------------------


CSS = """
@page {
  size: A4; margin: 22mm 18mm 20mm 18mm;
  @top-center { content: string(game); font-size: 9pt; color: #8a7f72;
                font-family: "DejaVu Sans", "Helvetica Neue", Arial, sans-serif; }
  @bottom-center { content: "page " counter(page) " / " counter(pages); font-size: 9pt; color: #8a7f72;
                   font-family: "DejaVu Sans", "Helvetica Neue", Arial, sans-serif; }
}
@page :first { @top-center { content: none; } @bottom-center { content: none; } }
body { font-family: "DejaVu Sans", "Helvetica Neue", Arial, sans-serif; font-size: 11pt;
       line-height: 1.45; color: #2b2622; }
h1, h2, h3 { font-family: "DejaVu Sans", "Helvetica Neue", Arial, sans-serif; break-after: avoid; }
.gamename { string-set: game content(); }
.cover { text-align: center; padding-top: 6mm; }
.cover .kicker { font-size: 13pt; letter-spacing: 1px; color: #e07a2f; font-weight: bold;
                 text-transform: uppercase; }
.cover h1 { font-size: 34pt; margin: 4mm 0 2mm; color: #2b2622; }
.cover .date { color: #8a7f72; margin-bottom: 8mm; }
.cover .app { width: 100%; border: 2px solid #2b2622; border-radius: 8px; }
.cover .final { width: 55%; border: 3px solid #2b2622; border-radius: 6px; image-rendering: pixelated; }
figure { margin: 4mm 0; text-align: center; break-inside: avoid; }
figcaption { font-size: 9.5pt; color: #6b6158; margin-top: 2mm; }
.shot { width: 48%; border: 3px solid #2b2622; border-radius: 6px; image-rendering: pixelated; }
.noshot { margin: 0 auto; width: 60%; padding: 10mm 4mm; border: 2px dashed #b9ad9f;
          border-radius: 6px; color: #8a7f72; font-size: 10pt; }
.chapter { break-before: page; font-size: 22pt; color: #e07a2f; margin: 0 0 4mm; }
.intro { color: #4a423b; }
.step { break-before: page; }
.step h2 { font-size: 18pt; margin: 0 0 3mm; }
.step h2 .num { display: inline-block; background: #e07a2f; color: white; border-radius: 6px;
                padding: 0 3mm; margin-right: 2mm; }
.ask { background: #fff3e0; border-left: 5px solid #e07a2f; border-radius: 4px;
       padding: 3mm 4mm; margin: 0 0 4mm; break-inside: avoid; }
.ask .who, .pix .who { font-weight: bold; font-size: 9.5pt; text-transform: uppercase;
                       letter-spacing: .5px; display: block; margin-bottom: 1mm; }
.ask .who { color: #b85c1c; }
.pix { background: #eaf4ff; border-left: 5px solid #3a7bd5; border-radius: 4px; padding: 3mm 4mm; }
.pix .who { color: #2a5ea8; }
.pix p { margin: 1.5mm 0; }
.pix ul, .pix ol { margin: 1mm 0; padding-left: 6mm; }
.pix h1, .pix h2, .pix h3 { font-size: 11.5pt; margin: 2mm 0 1mm; }
.pix code { font-family: "DejaVu Sans Mono", Menlo, monospace; font-size: 9.5pt;
            background: #d8e8fa; border-radius: 3px; padding: 0 1mm; }
.pix pre { background: #f6f8fb; border-radius: 4px; padding: 2mm 3mm; white-space: pre-wrap;
           break-inside: avoid; }
.pix pre code { background: none; padding: 0; }
h3.sub { font-size: 12.5pt; color: #2b2622; margin: 5mm 0 2mm; }
.nochange { color: #8a7f72; font-style: italic; }
table.code { width: 100%; border-collapse: collapse; font-family: "DejaVu Sans Mono", Menlo, monospace;
             font-size: 8.6pt; line-height: 1.35; background: #fbfaf7; border: 1px solid #e3ddd3; }
table.code td { padding: 0 2mm; vertical-align: top; }
table.code td.ln { width: 9mm; text-align: right; color: #a39888; border-right: 1px solid #e3ddd3;
                   user-select: none; }
table.code td.src { white-space: pre-wrap; word-break: break-all; }
table.code tr.add td { background: #e3f6e3; }
table.code.full { font-size: 8.2pt; line-height: 1.28; }
table.code.cont { border-top: none; }
.keep { break-inside: avoid; }
table.code tr.add td.ln { color: #2f8f3a; font-weight: bold; border-right: 3px solid #43a047; }
table.code tr.gap td { color: #a39888; text-align: left; }
table.code tr { break-inside: avoid; }
.legend { font-size: 9pt; color: #6b6158; margin: 1mm 0 2mm; }
.legend .box { display: inline-block; width: 3mm; height: 3mm; background: #e3f6e3;
               border-left: 3px solid #43a047; vertical-align: middle; }
.home pre { font-family: "DejaVu Sans Mono", Menlo, monospace; background: #2b2622; color: #f6efe6;
            padding: 3mm 4mm; border-radius: 5px; font-size: 10pt; }
.home li { margin: 1.5mm 0; }
.tip { background: #fff3e0; border-radius: 6px; padding: 3mm 4mm; margin-top: 5mm; }
"""


def build_story_pdf(d: Path) -> bytes:
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    name = meta.get("name", d.name)
    lang = i18n.norm_lang(meta.get("lang"))
    chat = d / "chat.json"
    messages = json.loads(chat.read_text(encoding="utf-8")) if chat.is_file() else []
    steps = _steps(d, messages)
    final_code = (d / "game.py").read_text(encoding="utf-8")
    has_res = (d / "res.pyxres").is_file()

    # Screenshots in parallel: each one runs the game in its own process.
    commits = list(dict.fromkeys([s["after"] for s in steps] + [_git(d, "rev-parse", "HEAD")]))
    commits = [c.strip() if c else None for c in commits]
    with ThreadPoolExecutor(max_workers=4) as pool:
        shots = dict(zip(commits, pool.map(lambda c: _screenshot(d, c), commits)))
    head = (_git(d, "rev-parse", "HEAD") or "").strip() or None
    final_shot = shots.get(head)

    e = html.escape

    def tx(key: str, **kwargs) -> str:
        return e(t(lang, key, **kwargs))

    css = CSS.replace('content: "page "', f'content: "{t(lang, "story_page")} "')
    parts = [f'<html lang="{lang}"><head><meta charset="utf-8"><style>{css}</style></head><body>']

    # Cover
    parts.append('<section class="cover">')
    parts.append(f'<div class="kicker">{tx("story_kicker")}</div>')
    parts.append(f'<h1 class="gamename">{e(_clean(name))}</h1>')
    parts.append(f'<div class="date">{i18n.format_date(lang, datetime.date.today())}</div>')
    if APP_SHOT.is_file():
        parts.append(_figure(_data_uri(APP_SHOT.read_bytes()), t(lang, "story_app_caption"),
                             cls="app", lang=lang))
    if final_shot:
        parts.append(_figure(final_shot, t(lang, "story_final_caption"), cls="final", lang=lang))
    parts.append("</section>")

    # Steps
    parts.append(f'<h1 class="chapter">{tx("story_chapter_steps")}</h1>')
    if not steps:
        parts.append(f'<p class="intro">{tx("story_no_steps")}</p>')
    else:
        word = t(lang, "story_step_many" if len(steps) > 1 else "story_step_one")
        # This string holds markup (<b>), so it is not escaped.
        parts.append(f'<p class="intro">{t(lang, "story_intro_steps", n=len(steps), steps=word)}</p>')
    for n, s in enumerate(steps, 1):
        cls = "step" if n > 1 else "step first"
        parts.append(f'<section class="{cls}"' + (' style="break-before:auto"' if n == 1 else "") + ">")
        parts.append(f'<h2><span class="num">{tx("story_step", n=n)}</span></h2>')
        parts.append(f'<div class="ask"><span class="who">{tx("story_you_asked")}</span>{e(_clean(s["ask"]))}</div>')
        parts.append(f'<div class="pix"><span class="who">{tx("story_pix_explained")}</span>'
                     f'{_answer_html(s["answer"], lang)}</div>')
        parts.append(_figure(shots.get(s["after"]), t(lang, "story_after_step", n=n), lang=lang))
        before = _show(d, s["before"], "game.py") if s["before"] else None
        after = _show(d, s["after"], "game.py") if s["after"] else None
        title = f'<h3 class="sub">{tx("story_step_code")}</h3>'
        rows = _extract((before or b"").decode("utf-8", "replace"),
                        after.decode("utf-8", "replace")) if after is not None else None
        if rows:
            parts.append(_code_block(title, rows, legend=True, lang=lang))
        else:
            parts.append(title + f'<p class="nochange">{tx("story_no_change")}</p>')
        parts.append("</section>")

    # Full code
    parts.append(f'<h1 class="chapter">{tx("story_chapter_code")}</h1>')
    parts.append(f'<p class="intro">{t(lang, "story_code_intro", lines=len(final_code.splitlines()))}</p>')
    lines = _highlight_lines(final_code.rstrip("\n"))
    parts.append(_code_block("", [(i + 1, src, False) for i, src in enumerate(lines)], cls="code full", lang=lang))

    # At home (these strings hold markup, so they are not escaped)
    parts.append(f'<section class="home"><h1 class="chapter">{tx("story_chapter_home")}</h1>')
    parts.append(f"<ol><li>{t(lang, 'story_home_install')}"
                 "<pre>pip install pyxel</pre></li>"
                 f"<li>{t(lang, 'story_home_file')}"
                 + (t(lang, "story_home_res") if has_res else "")
                 + f"{t(lang, 'story_home_export')}</li>"
                 f"<li>{t(lang, 'story_home_run')}<pre>pyxel run game.py</pre></li>"
                 + (f"<li>{t(lang, 'story_home_edit')}<pre>pyxel edit res.pyxres</pre></li>" if has_res else "")
                 + "</ol>")
    parts.append(f'<div class="tip"><b>{tx("story_tip_title")}</b><ul>'
                 f"<li>{tx('story_tip_1')}</li>"
                 f"<li>{tx('story_tip_2')}</li>"
                 f"<li>{tx('story_tip_3')}</li>"
                 f"</ul>{tx('story_tip_end')}</div>")
    parts.append("</section></body></html>")
    return HTML(string="".join(parts), base_url=str(HERE)).write_pdf()
