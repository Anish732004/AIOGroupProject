#!/usr/bin/env python3
"""
Build the GenAI Prompt Log PDF for Blackboard (plan §5.2 step 10, §6.1) from the three markdown logs in docs/.

    python tools/build_prompt_log_pdf.py      # needs Google Chrome (headless print); writes docs/GenAI_Prompt_Log.pdf

The markdown logs stay the source of truth; re-run this after editing them.
"""
from __future__ import annotations

import html
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ["GENAI_PROMPT_LOG_layer1.md", "GENAI_PROMPT_LOG_layer2_3.md", "GENAI_PROMPT_LOG_layer4_5.md"]
OUT = ROOT / "docs" / "GenAI_Prompt_Log.pdf"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: m.group(1) if m.group(2).endswith(".md") else
               f'<a href="{m.group(2)}">{m.group(1)}</a>', t)
    return t


def md_to_html(text: str) -> str:
    out, para, lst, table = [], [], [], []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
        if lst:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in lst) + "</ul>"); lst.clear()
        if table:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table if not re.match(r"^\|[\s:|-]+\|$", r.strip())]
            head, body = rows[0], rows[1:]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>" +
                       "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table>")
            table.clear()

    for line in text.splitlines():
        s = line.rstrip()
        if s.startswith("|"):
            if para or lst:
                flush()
            table.append(s); continue
        if table:
            flush()
        m = re.match(r"^(#{1,3})\s+(.*)", s)
        if m:
            flush(); lvl = len(m.group(1)) + 1
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>"); continue
        if re.match(r"^\s*[*-]\s+", s):
            if para:
                out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
            lst.append(re.sub(r"^\s*[*-]\s+", "", s)); continue
        if lst and s.startswith("  ") and s.strip():
            lst[-1] += " " + s.strip(); continue
        if not s.strip():
            flush(); continue
        para.append(s.strip())
    flush()
    return "\n".join(out)


def main() -> int:
    parts = []
    for name in LOGS:
        parts.append(f'<section class="log">{md_to_html((ROOT / "docs" / name).read_text())}</section>')
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>GenAI Prompt Log</title><style>
@page {{ size: A4; margin: 16mm 14mm; }}
body {{ font: 10.5px/1.45 -apple-system, "Segoe UI", Roboto, sans-serif; color: #111; }}
h1 {{ font-size: 20px; margin: 0 0 4px; }} h2 {{ font-size: 15px; margin: 18px 0 6px; }} h3 {{ font-size: 12.5px; margin: 14px 0 6px; }}
.log {{ page-break-before: always; }} .cover p {{ font-size: 12px; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0; page-break-inside: auto; }}
th, td {{ border: 1px solid #bbb; padding: 4px 6px; vertical-align: top; text-align: left; }}
tr {{ page-break-inside: avoid; }} th {{ background: #f0f0ee; }}
code {{ font: 9.5px ui-monospace, Menlo, monospace; background: #f3f3f1; padding: 0 2px; word-break: break-word; }}
a {{ color: #1c5cab; }} .box {{ border: 2px dashed #d03b3b; padding: 10px 12px; margin: 14px 0; }}
</style></head><body>
<section class="cover"><h1>PharmaShield GCC — GenAI Prompt Log</h1>
<p>AI in Operations · Group 3 · prepared {date.today():%d %B %Y}</p>
<div class="box"><strong>Disclosure protocol (plan §6.1).</strong> Every GenAI-assisted slide text, visual or code snippet is marked
on the slides with a red dashed outline like this box and footnoted "Circled = GenAI-generated; prompts in Appendix". This
document is that appendix: the prompts given to the AI assistant (Claude, by Anthropic, used through Claude Code), word for word,
and what each one produced, layer by layer.</div>
<p>Contents: 1. Layer 1 (data ingestion) · 2. Layers 2 and 3 (entity resolution and AI risk engines) · 3. Layers 4 and 5
(decision engine, cockpit and website), the stress test and the synthetic view. Each part ends with what is and is not
AI-generated data. All team decisions are recorded in <code>docs/DECISIONS.md</code> in the code submission.</p></section>
{''.join(parts)}</body></html>"""
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "prompt_log.html"
        page.write_text(doc)
        if not Path(CHROME).exists():
            print(f"Chrome not found at {CHROME}; set CHROME=... (HTML left at {page})"); return 1
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={OUT}", page.as_uri()], check=True, capture_output=True, timeout=120)
    print(f"written: {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
