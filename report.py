#!/usr/bin/env python3
"""Turn a CAPE attempt record.json into a self-contained HTML document."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def load_vector_config() -> dict:
    return json.loads((ROOT / "config" / "vector_config.json").read_text(encoding="utf-8"))


def _e(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _pre(value: Any) -> str:
    text = "" if value is None else str(value)
    return f"<pre>{_e(text)}</pre>"


def _verdict_class(verdict: str) -> str:
    v = (verdict or "").upper()
    if "EXEMPTED" in v and "NOT EXEMPTED" not in v:
        return "verdict-exempt"
    if "BORDERLINE" in v:
        return "verdict-borderline"
    if "FAIL" in v:
        return "verdict-fail"
    return "verdict-pass"


def _score_cell(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _e(value)
    if number == int(number):
        return str(int(number))
    return f"{number:.1f}"


def render_report(record: dict[str, Any], vector_config: dict | None = None) -> str:
    vector_config = vector_config or load_vector_config()
    dimensions = (vector_config or {}).get("dimensions") or {}
    sheet = record.get("score_sheet") or {}
    verdict = record.get("verdict") or sheet.get("verdict") or "UNKNOWN"
    skills = sheet.get("skill_final") or {}
    vectors = sheet.get("vector_final") or {}
    pass_a = sheet.get("pass_a") or record.get("pass_a") or {}
    pass_b = sheet.get("pass_b") or record.get("pass_b") or {}
    evidence_a = pass_a.get("evidence") or {}
    evidence_b = pass_b.get("evidence") or {}
    submission = record.get("submission") or {}
    defense = record.get("defense_qa") or []
    tools = record.get("tools") or []
    tools_text = ", ".join(str(t) for t in tools) if tools else "—"
    cloud = record.get("hyperscaler") or "None"
    github = record.get("github_url") or ""
    report_url = record.get("html_report_url") or ""
    recorded = record.get("recorded_at") or ""

    skill_rows = []
    for name, item in skills.items():
        flag = "Yes" if item.get("borderline_review") else "—"
        a_score = (pass_a.get("skill_scores") or {}).get(name, "—")
        b_score = (pass_b.get("skill_scores") or {}).get(name, "—")
        skill_rows.append(
            "<tr>"
            f"<td>{_e(name)}</td>"
            f"<td class='num'>{_e(_score_cell(a_score))}</td>"
            f"<td class='num'>{_e(_score_cell(b_score))}</td>"
            f"<td class='num'><strong>{_e(_score_cell(item.get('final')))}</strong></td>"
            f"<td class='num'>{_e(_score_cell(item.get('disagreement', 0)))}</td>"
            f"<td>{_e(flag)}</td>"
            "</tr>"
        )

    vector_rows = []
    for code, item in vectors.items():
        dim_name = (dimensions.get(code) or {}).get("name") or code
        flag = "Yes" if item.get("borderline_review") else "—"
        a_score = (pass_a.get("vector_scores") or {}).get(code, "—")
        b_score = (pass_b.get("vector_scores") or {}).get(code, "—")
        vector_rows.append(
            "<tr>"
            f"<td><span class='code'>{_e(code)}</span> {_e(dim_name)}</td>"
            f"<td class='num'>{_e(_score_cell(a_score))}</td>"
            f"<td class='num'>{_e(_score_cell(b_score))}</td>"
            f"<td class='num'><strong>{_e(_score_cell(item.get('final')))}</strong></td>"
            f"<td class='num'>{_e(_score_cell(item.get('disagreement', 0)))}</td>"
            f"<td>{_e(flag)}</td>"
            "</tr>"
        )

    evidence_keys = []
    for key in list(skills.keys()) + list(vectors.keys()):
        if key not in evidence_keys:
            evidence_keys.append(key)
    for key in list(evidence_a.keys()) + list(evidence_b.keys()):
        if key not in evidence_keys:
            evidence_keys.append(key)

    evidence_blocks = []
    for key in evidence_keys:
        dim_name = (dimensions.get(key) or {}).get("name")
        label = f"{key} — {dim_name}" if dim_name else key
        evidence_blocks.append(
            "<article class='evidence'>"
            f"<h3>{_e(label)}</h3>"
            f"<p><span class='pill'>Assessor A</span> {_e(evidence_a.get(key) or '—')}</p>"
            f"<p><span class='pill'>Assessor B</span> {_e(evidence_b.get(key) or '—')}</p>"
            "</article>"
        )

    qa_blocks = []
    for i, pair in enumerate(defense, start=1):
        qa_blocks.append(
            "<article class='qa'>"
            f"<h3>Question {i}</h3>"
            f"<p class='question'>{_e(pair.get('question'))}</p>"
            f"<p class='answer'>{_e(pair.get('answer') or '(no answer)')}</p>"
            "</article>"
        )

    github_html = (
        f'<p><a href="{_e(github)}">JSON audit record on GitHub</a></p>' if github else ""
    )
    report_link_html = (
        f'<p><a href="{_e(report_url)}">HTML report on GitHub</a></p>' if report_url else ""
    )

    title = (
        f"CAPE Report — {_e(record.get('candidate_name') or 'Candidate')} — "
        f"Module {_e(record.get('module_id'))}"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --ink: #162033;
      --muted: #5b6578;
      --line: #d8d2c4;
      --paper: #fbf7ef;
      --panel: #ffffff;
      --navy: #0f2744;
      --gold: #b8893a;
      --pass: #1f6b4a;
      --fail: #9b2c2c;
      --warn: #8a5a12;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font: 16px/1.55 "Source Serif 4", "Georgia", serif;
    }}
    header.hero {{
      background: var(--navy);
      color: #f4ead4;
      padding: 40px 8vw 36px;
    }}
    header.hero p.kicker {{
      letter-spacing: 0.18em;
      text-transform: uppercase;
      font: 12px/1.4 "Segoe UI", sans-serif;
      margin: 0 0 10px;
      color: var(--gold);
    }}
    header.hero h1 {{
      font-size: 2rem;
      font-weight: 600;
      margin: 0 0 8px;
    }}
    header.hero .meta {{
      font: 14px/1.5 "Segoe UI", sans-serif;
      opacity: 0.9;
    }}
    main {{ max-width: 920px; margin: 0 auto; padding: 28px 8vw 64px; }}
    .verdict {{
      margin: -28px 0 28px;
      padding: 18px 22px;
      border-radius: 6px;
      color: white;
      font: 600 1.05rem/1.4 "Segoe UI", sans-serif;
    }}
    .verdict-exempt {{ background: var(--pass); }}
    .verdict-pass {{ background: #2c5282; }}
    .verdict-fail {{ background: var(--fail); }}
    .verdict-borderline {{ background: var(--warn); }}
    .scores {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-bottom: 32px;
    }}
    .score-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 16px 18px;
    }}
    .score-card span {{
      display: block;
      font: 11px/1.3 "Segoe UI", sans-serif;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .score-card strong {{ font-size: 1.8rem; font-weight: 600; }}
    h2 {{
      font-size: 1.25rem;
      border-bottom: 1px solid var(--line);
      padding-bottom: 6px;
      margin: 36px 0 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      font: 14px/1.4 "Segoe UI", sans-serif;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #efe8d8;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      font-size: 11px;
    }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .code {{
      display: inline-block;
      min-width: 1.4em;
      font-weight: 700;
      color: var(--gold);
    }}
    .evidence, .qa {{
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 14px 16px;
      margin: 0 0 12px;
    }}
    .evidence h3, .qa h3 {{ margin: 0 0 8px; font-size: 1rem; }}
    .pill {{
      display: inline-block;
      font: 600 10px/1 "Segoe UI", sans-serif;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: #efe8d8;
      padding: 3px 7px;
      margin-right: 8px;
      color: var(--navy);
    }}
    .question {{ font-style: italic; }}
    .answer {{ white-space: pre-wrap; }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #fff;
      border: 1px solid var(--line);
      padding: 16px;
      font: 13px/1.45 "Consolas", "Menlo", monospace;
    }}
    a {{ color: #1a4f86; }}
    footer {{
      margin-top: 48px;
      color: var(--muted);
      font: 13px/1.5 "Segoe UI", sans-serif;
    }}
    @media (max-width: 720px) {{
      .scores {{ grid-template-columns: 1fr; }}
      header.hero, main {{ padding-left: 20px; padding-right: 20px; }}
    }}
    @media print {{
      header.hero {{ padding: 24px 0; background: #000; }}
      main {{ padding: 12px 0 0; }}
      a {{ color: inherit; text-decoration: none; }}
    }}
  </style>
</head>
<body>
  <header class="hero">
    <p class="kicker">G.A.Menon Academy · Capability Assessment &amp; Proficiency Engine</p>
    <h1>{_e(record.get("candidate_name") or "Candidate")}</h1>
    <p class="meta">
      Module {_e(record.get("module_id"))}: {_e(record.get("module_name"))}<br />
      Domain: {_e(record.get("domain"))} · Tools: {_e(tools_text)} · Cloud: {_e(cloud)}
      {f'<br />Recorded: {_e(recorded)}' if recorded else ''}
    </p>
  </header>
  <main>
    <div class="verdict {_verdict_class(verdict)}">Verdict: {_e(verdict)}</div>
    <section class="scores">
      <div class="score-card"><span>Module score</span><strong>{_e(_score_cell(sheet.get("module_score")))}</strong></div>
      <div class="score-card"><span>VECTOR score</span><strong>{_e(_score_cell(sheet.get("vector_score")))}</strong></div>
      <div class="score-card"><span>Blended (60 / 40)</span><strong>{_e(_score_cell(sheet.get("final_blended_score")))}</strong></div>
    </section>

    <h2>Skill indices</h2>
    <table>
      <thead><tr><th>Skill</th><th>A</th><th>B</th><th>Final</th><th>Gap</th><th>Human review</th></tr></thead>
      <tbody>
        {''.join(skill_rows) or '<tr><td colspan="6">No skill scores recorded.</td></tr>'}
      </tbody>
    </table>

    <h2>VECTOR dimensions</h2>
    <table>
      <thead><tr><th>Dimension</th><th>A</th><th>B</th><th>Final</th><th>Gap</th><th>Human review</th></tr></thead>
      <tbody>
        {''.join(vector_rows) or '<tr><td colspan="6">No VECTOR scores recorded.</td></tr>'}
      </tbody>
    </table>

    <h2>Assessor evidence</h2>
    {''.join(evidence_blocks) or '<p>No evidence notes recorded.</p>'}

    <h2>Capstone problem</h2>
    {_pre(record.get("problem_statement"))}

    <h2>Written submission</h2>
    {_pre(submission.get("written"))}

    <h2>Code submission</h2>
    {_pre(submission.get("code"))}

    <h2>Defense</h2>
    {''.join(qa_blocks) or '<p>No defense questions recorded.</p>'}

    <h2>Audit trail</h2>
    {github_html}
    {report_link_html}
    <p>Generation model: {_e(record.get("generation_model") or "—")}</p>
  </main>
  <footer>
    <p>Final blended score = (module skill average × 0.6) + (VECTOR average × 0.4). Exemption requires a blended score of at least 75 and no skill or VECTOR dimension below 50. Disagreement above 25 points flags human review and keeps the lower score.</p>
  </footer>
</body>
</html>
"""


def write_report(record_path: Path, output_path: Path | None = None) -> Path:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    html_doc = render_report(record)
    dest = output_path or record_path.with_name("report.html")
    dest.write_text(html_doc, encoding="utf-8")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a CAPE record.json file into a formatted HTML report."
    )
    parser.add_argument("record", help="Path to record.json")
    parser.add_argument("-o", "--output", help="Where to write report.html")
    parser.add_argument("--stdout", action="store_true", help="Print HTML instead of writing a file")
    args = parser.parse_args()
    path = Path(args.record)
    record = json.loads(path.read_text(encoding="utf-8"))
    html_doc = render_report(record)
    if args.stdout:
        sys.stdout.write(html_doc)
        return 0
    dest = Path(args.output) if args.output else path.with_name("report.html")
    dest.write_text(html_doc, encoding="utf-8")
    print(f"Wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
