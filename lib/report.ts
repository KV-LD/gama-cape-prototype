import { loadVector } from "./config";
import type { AttemptRecord } from "./types";

function escapeHtml(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function asPre(value: unknown): string {
  return `<pre>${escapeHtml(value ?? "")}</pre>`;
}

function verdictClass(verdict: string): string {
  const v = (verdict || "").toUpperCase();
  if (v.includes("EXEMPTED") && !v.includes("NOT EXEMPTED")) return "verdict-exempt";
  if (v.includes("BORDERLINE")) return "verdict-borderline";
  if (v.includes("FAIL")) return "verdict-fail";
  return "verdict-pass";
}

function scoreCell(value: unknown): string {
  const number = Number(value);
  if (!Number.isFinite(number)) return escapeHtml(value);
  if (number === Math.trunc(number)) return String(Math.trunc(number));
  return number.toFixed(1);
}

export function renderReport(record: AttemptRecord): string {
  const vectorConfig = loadVector();
  const dimensions = vectorConfig.dimensions || {};
  const sheet = record.score_sheet || ({} as AttemptRecord["score_sheet"]);
  const verdict = record.verdict || sheet.verdict || "UNKNOWN";
  const skills = sheet.skill_final || {};
  const vectors = sheet.vector_final || {};
  const passA = sheet.pass_a || record.pass_a;
  const passB = sheet.pass_b || record.pass_b;
  const evidenceA = passA?.evidence || {};
  const evidenceB = passB?.evidence || {};
  const submission = record.submission || { written: "", code: "", text: "" };
  const defense = record.defense_qa || [];
  const toolsText = record.tools?.length ? record.tools.join(", ") : "—";
  const cloud = record.hyperscaler || "None";

  const skillRows = Object.entries(skills).map(([name, item]) => {
    const flag = item.borderline_review ? "Yes" : "—";
    const aScore = passA?.skill_scores?.[name] ?? "—";
    const bScore = passB?.skill_scores?.[name] ?? "—";
    return `<tr><td>${escapeHtml(name)}</td><td class='num'>${escapeHtml(scoreCell(aScore))}</td><td class='num'>${escapeHtml(scoreCell(bScore))}</td><td class='num'><strong>${escapeHtml(scoreCell(item.final))}</strong></td><td class='num'>${escapeHtml(scoreCell(item.disagreement || 0))}</td><td>${escapeHtml(flag)}</td></tr>`;
  });

  const vectorRows = Object.entries(vectors).map(([code, item]) => {
    const dimName = dimensions[code]?.name || code;
    const flag = item.borderline_review ? "Yes" : "—";
    const aScore = passA?.vector_scores?.[code] ?? "—";
    const bScore = passB?.vector_scores?.[code] ?? "—";
    return `<tr><td><span class='code'>${escapeHtml(code)}</span> ${escapeHtml(dimName)}</td><td class='num'>${escapeHtml(scoreCell(aScore))}</td><td class='num'>${escapeHtml(scoreCell(bScore))}</td><td class='num'><strong>${escapeHtml(scoreCell(item.final))}</strong></td><td class='num'>${escapeHtml(scoreCell(item.disagreement || 0))}</td><td>${escapeHtml(flag)}</td></tr>`;
  });

  const evidenceKeys: string[] = [
    ...Object.keys(skills),
    ...Object.keys(vectors),
    ...Object.keys(evidenceA),
    ...Object.keys(evidenceB),
  ].filter((key, index, all) => all.indexOf(key) === index);

  const evidenceBlocks = evidenceKeys.map((key) => {
    const dimName = dimensions[key]?.name;
    const label = dimName ? `${key} — ${dimName}` : key;
    return `<article class='evidence'><h3>${escapeHtml(label)}</h3><p><span class='pill'>Assessor A</span> ${escapeHtml(evidenceA[key] || "—")}</p><p><span class='pill'>Assessor B</span> ${escapeHtml(evidenceB[key] || "—")}</p></article>`;
  });

  const qaBlocks = defense.map((pair, i) => {
    return `<article class='qa'><h3>Question ${i + 1}</h3><p class='question'>${escapeHtml(pair.question)}</p><p class='answer'>${escapeHtml(pair.answer || "(no answer)")}</p></article>`;
  });

  const githubHtml = record.github_url
    ? `<p><a href="${escapeHtml(record.github_url)}">JSON audit record on GitHub</a></p>`
    : "";
  const reportLinkHtml = record.html_report_url
    ? `<p><a href="${escapeHtml(record.html_report_url)}">HTML report on GitHub</a></p>`
    : "";
  const recorded = record.recorded_at
    ? `<br />Recorded: ${escapeHtml(record.recorded_at)}`
    : "";
  const title = `CAPE Report — ${escapeHtml(record.candidate_name || "Candidate")} — Module ${escapeHtml(record.module_id)}`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${title}</title>
  <style>
    :root { --ink:#162033; --muted:#5b6578; --line:#d8d2c4; --paper:#fbf7ef; --panel:#fff; --navy:#0f2744; --gold:#b8893a; --pass:#1f6b4a; --fail:#9b2c2c; --warn:#8a5a12; }
    * { box-sizing: border-box; }
    body { margin:0; background:var(--paper); color:var(--ink); font:16px/1.55 Georgia, serif; }
    header.hero { background:var(--navy); color:#f4ead4; padding:40px 8vw 36px; }
    header.hero p.kicker { letter-spacing:.18em; text-transform:uppercase; font:12px/1.4 Segoe UI, sans-serif; margin:0 0 10px; color:var(--gold); }
    header.hero h1 { font-size:2rem; font-weight:600; margin:0 0 8px; }
    header.hero .meta { font:14px/1.5 Segoe UI, sans-serif; opacity:.9; }
    main { max-width:920px; margin:0 auto; padding:28px 8vw 64px; }
    .verdict { margin:-28px 0 28px; padding:18px 22px; border-radius:6px; color:#fff; font:600 1.05rem/1.4 Segoe UI, sans-serif; }
    .verdict-exempt { background:var(--pass); } .verdict-pass { background:#2c5282; } .verdict-fail { background:var(--fail); } .verdict-borderline { background:var(--warn); }
    .scores { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:32px; }
    .score-card { background:var(--panel); border:1px solid var(--line); padding:16px 18px; }
    .score-card span { display:block; font:11px/1.3 Segoe UI, sans-serif; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }
    .score-card strong { font-size:1.8rem; font-weight:600; }
    h2 { font-size:1.25rem; border-bottom:1px solid var(--line); padding-bottom:6px; margin:36px 0 14px; }
    table { width:100%; border-collapse:collapse; background:var(--panel); font:14px/1.4 Segoe UI, sans-serif; }
    th, td { border-bottom:1px solid var(--line); padding:10px 12px; text-align:left; vertical-align:top; }
    th { background:#efe8d8; font-weight:600; letter-spacing:.04em; text-transform:uppercase; font-size:11px; }
    td.num { text-align:right; font-variant-numeric:tabular-nums; }
    .code { display:inline-block; min-width:1.4em; font-weight:700; color:var(--gold); }
    .evidence, .qa { background:var(--panel); border:1px solid var(--line); padding:14px 16px; margin:0 0 12px; }
    .evidence h3, .qa h3 { margin:0 0 8px; font-size:1rem; }
    .pill { display:inline-block; font:600 10px/1 Segoe UI, sans-serif; letter-spacing:.08em; text-transform:uppercase; background:#efe8d8; padding:3px 7px; margin-right:8px; color:var(--navy); }
    .question { font-style:italic; } .answer { white-space:pre-wrap; }
    pre { white-space:pre-wrap; word-break:break-word; background:#fff; border:1px solid var(--line); padding:16px; font:13px/1.45 Consolas, Menlo, monospace; }
    a { color:#1a4f86; }
    footer { margin-top:48px; color:var(--muted); font:13px/1.5 Segoe UI, sans-serif; }
    @media (max-width:720px) { .scores { grid-template-columns:1fr; } header.hero, main { padding-left:20px; padding-right:20px; } }
    @media print { header.hero { padding:24px 0; } main { padding:12px 0 0; } a { color:inherit; text-decoration:none; } }
  </style>
</head>
<body>
  <header class="hero">
    <p class="kicker">G.A.Menon Academy · Capability Assessment &amp; Proficiency Engine</p>
    <h1>${escapeHtml(record.candidate_name || "Candidate")}</h1>
    <p class="meta">
      Module ${escapeHtml(record.module_id)}: ${escapeHtml(record.module_name)}<br />
      Domain: ${escapeHtml(record.domain)} · Tools: ${escapeHtml(toolsText)} · Cloud: ${escapeHtml(cloud)}
      ${recorded}
    </p>
  </header>
  <main>
    <div class="verdict ${verdictClass(verdict)}">Verdict: ${escapeHtml(verdict)}</div>
    <section class="scores">
      <div class="score-card"><span>Module score</span><strong>${escapeHtml(scoreCell(sheet.module_score))}</strong></div>
      <div class="score-card"><span>VECTOR score</span><strong>${escapeHtml(scoreCell(sheet.vector_score))}</strong></div>
      <div class="score-card"><span>Blended (60 / 40)</span><strong>${escapeHtml(scoreCell(sheet.final_blended_score))}</strong></div>
    </section>
    <h2>Skill indices</h2>
    <table>
      <thead><tr><th>Skill</th><th>A</th><th>B</th><th>Final</th><th>Gap</th><th>Human review</th></tr></thead>
      <tbody>${skillRows.join("") || '<tr><td colspan="6">No skill scores recorded.</td></tr>'}</tbody>
    </table>
    <h2>VECTOR dimensions</h2>
    <table>
      <thead><tr><th>Dimension</th><th>A</th><th>B</th><th>Final</th><th>Gap</th><th>Human review</th></tr></thead>
      <tbody>${vectorRows.join("") || '<tr><td colspan="6">No VECTOR scores recorded.</td></tr>'}</tbody>
    </table>
    <h2>Assessor evidence</h2>
    ${evidenceBlocks.join("") || "<p>No evidence notes recorded.</p>"}
    <h2>Capstone problem</h2>
    ${asPre(record.problem_statement)}
    <h2>Written submission</h2>
    ${asPre(submission.written)}
    <h2>Code submission</h2>
    ${asPre(submission.code)}
    <h2>Defense</h2>
    ${qaBlocks.join("") || "<p>No defense questions recorded.</p>"}
    <h2>Audit trail</h2>
    ${githubHtml}
    ${reportLinkHtml}
    <p>Generation model: ${escapeHtml(record.generation_model || "—")}</p>
  </main>
  <footer>
    <p>Final blended score = (module skill average × 0.6) + (VECTOR average × 0.4). Exemption requires a blended score of at least 75 and no skill or VECTOR dimension below 50. Disagreement above 25 points flags human review and keeps the lower score.</p>
  </footer>
</body>
</html>`;
}
