"use client";

import { useEffect, useMemo, useState } from "react";

type ModuleInfo = {
  id: number;
  name: string;
  exemptible: boolean;
  phase_ref?: string;
};

type ConfigPayload = {
  domains: string[];
  tools: string[];
  hyperscalers: string[];
  modules: ModuleInfo[];
};

type ScorePass = {
  pass_label: string;
  skill_scores: Record<string, number>;
  vector_scores: Record<string, number>;
  evidence: Record<string, string>;
};

const STEPS = [
  { id: 1, label: "Profile" },
  { id: 2, label: "Capstone" },
  { id: 3, label: "Submission" },
  { id: 4, label: "Defense" },
  { id: 5, label: "Scoring" },
  { id: 6, label: "Report" },
];

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = (await resp.json()) as T & { error?: string };
  if (!resp.ok) throw new Error(data.error || `Request failed (${resp.status})`);
  return data;
}

export default function CapeApp() {
  const [config, setConfig] = useState<ConfigPayload | null>(null);
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [moduleId, setModuleId] = useState<number | "">("");
  const [tools, setTools] = useState<string[]>([]);
  const [hyperscaler, setHyperscaler] = useState("None");

  const [problem, setProblem] = useState("");
  const [generationPrompt, setGenerationPrompt] = useState("");
  const [generationModel, setGenerationModel] = useState("");
  const [written, setWritten] = useState("");
  const [code, setCode] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<string[]>([]);
  const [status, setStatus] = useState("");
  const [html, setHtml] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [htmlUrl, setHtmlUrl] = useState("");
  const [verdict, setVerdict] = useState("");

  useEffect(() => {
    fetch("/api/config")
      .then((r) => r.json())
      .then(setConfig)
      .catch((err) => setError(err.message || "Could not load modules."));
  }, []);

  const selectedModule = useMemo(
    () => config?.modules.find((m) => m.id === moduleId),
    [config, moduleId],
  );

  function toggleTool(tool: string) {
    setTools((current) =>
      current.includes(tool) ? current.filter((item) => item !== tool) : [...current, tool],
    );
  }

  async function generateCapstone() {
    setError("");
    if (!name.trim()) return setError("Please enter your name.");
    if (!domain) return setError("Please choose a domain.");
    if (!moduleId) return setError("Please choose a module.");
    if (!tools.length) return setError("Pick at least one AI tool.");
    setBusy("Writing a fresh capstone brief. This can take up to a minute...");
    try {
      const result = await postJson<{
        problem_statement: string;
        generation_prompt: string;
        generation_model: string;
      }>("/api/generate", {
        module_id: moduleId,
        domain,
        tools,
        hyperscaler,
      });
      setProblem(result.problem_statement);
      setGenerationPrompt(result.generation_prompt);
      setGenerationModel(result.generation_model);
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate the capstone.");
    } finally {
      setBusy("");
    }
  }

  async function startDefense() {
    setError("");
    if (!written.trim()) return setError("Paste your written notes before continuing.");
    setBusy("Reading your work and writing defense questions...");
    try {
      const result = await postJson<{ questions: string[] }>("/api/defense", {
        module_id: moduleId,
        submission: { written, code },
      });
      setQuestions(result.questions);
      setAnswers(result.questions.map(() => ""));
      setStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the defense.");
    } finally {
      setBusy("");
    }
  }

  async function runScoring() {
    setError("");
    if (answers.some((answer) => !answer.trim())) {
      return setError("Please answer every defense question.");
    }
    setStep(5);
    const defenseQa = questions.map((question, i) => ({ question, answer: answers[i] }));
    const submission = { written, code };
    try {
      setStatus("Assessor A is scoring...");
      setBusy("Two independent assessors are scoring your work.");
      const passA = await postJson<ScorePass>("/api/score-pass", {
        module_id: moduleId,
        submission,
        defense_qa: defenseQa,
        pass_label: "Assessor A",
      });
      setStatus("Assessor B is scoring...");
      const passB = await postJson<ScorePass>("/api/score-pass", {
        module_id: moduleId,
        submission,
        defense_qa: defenseQa,
        pass_label: "Assessor B",
      });
      setStatus("Saving the JSON audit record and HTML report to GitHub...");
      const finalized = await postJson<{
        html: string;
        record: {
          verdict: string;
          github_url?: string;
          html_report_url?: string;
        };
      }>("/api/finalize", {
        candidate_name: name.trim(),
        domain,
        module_id: moduleId,
        tools,
        hyperscaler,
        problem_statement: problem,
        generation_prompt: generationPrompt,
        generation_model: generationModel,
        submission,
        defense_qa: defenseQa,
        pass_a: passA,
        pass_b: passB,
      });
      setHtml(finalized.html);
      setVerdict(finalized.record.verdict);
      setGithubUrl(finalized.record.github_url || "");
      setHtmlUrl(finalized.record.html_report_url || "");
      setStep(6);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scoring failed.");
      setStep(4);
    } finally {
      setBusy("");
      setStatus("");
    }
  }

  function downloadHtml() {
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `cape-report-${name.replace(/\s+/g, "_")}-module-${moduleId}.html`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="shell">
      <header className="brand">
        <div>
          <p>G.A.Menon Academy</p>
          <h1>Capability Assessment &amp; Proficiency Engine</h1>
        </div>
        <nav>
          <a href="/">Assessment</a>
          <a href="/report">JSON → HTML</a>
        </nav>
      </header>

      <div className="layout">
        <aside className="steps">
          <ol>
            {STEPS.map((item) => (
              <li
                key={item.id}
                className={item.id === step ? "active" : item.id < step ? "done" : ""}
              >
                <strong>
                  {item.id}. {item.label}
                </strong>
              </li>
            ))}
          </ol>
        </aside>

        <section className="card">
          {error ? <div className="error">{error}</div> : null}
          {busy ? <div className="notice">{busy}</div> : null}

          {step === 1 && (
            <>
              <h2>Start an assessment</h2>
              <p className="lede">
                Same flow as the command-line prototype: profile, a generated capstone, your
                work, a short defense, then a two-pass score saved to GitHub.
              </p>
              <label htmlFor="name">Your name</label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
              />
              <div className="row">
                <div>
                  <label htmlFor="domain">Industry domain</label>
                  <select
                    id="domain"
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                  >
                    <option value="">Choose one</option>
                    {(config?.domains || []).map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="module">FDE module</label>
                  <select
                    id="module"
                    value={moduleId}
                    onChange={(e) => setModuleId(e.target.value ? Number(e.target.value) : "")}
                  >
                    <option value="">Choose one</option>
                    {(config?.modules || []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.id}. {item.name}
                        {item.exemptible ? "" : " (not exemptible)"}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <label>AI tools you used</label>
              <div className="chips">
                {(config?.tools || []).map((tool) => (
                  <button
                    type="button"
                    key={tool}
                    className={tools.includes(tool) ? "chip on" : "chip"}
                    onClick={() => toggleTool(tool)}
                  >
                    {tool}
                  </button>
                ))}
              </div>
              <label htmlFor="cloud">Cloud (hyperscaler)</label>
              <select
                id="cloud"
                value={hyperscaler}
                onChange={(e) => setHyperscaler(e.target.value)}
              >
                {(config?.hyperscalers || ["None"]).map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
              <div className="actions">
                <button type="button" onClick={generateCapstone} disabled={!!busy}>
                  Generate capstone
                </button>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <h2>Your capstone problem</h2>
              <p className="lede">
                {selectedModule
                  ? `Module ${selectedModule.id}: ${selectedModule.name}`
                  : "Read this brief, then continue when you are ready to paste your work."}
              </p>
              <div className="problem">{problem}</div>
              <div className="actions">
                <button type="button" className="secondary" onClick={() => setStep(1)}>
                  Back
                </button>
                <button type="button" onClick={() => setStep(3)}>
                  I am ready to submit
                </button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <h2>Paste your work</h2>
              <p className="lede">
                Written notes first, then code. You can leave code empty if this module is
                document-only.
              </p>
              <label htmlFor="written">Written notes / architecture docs</label>
              <textarea
                id="written"
                value={written}
                onChange={(e) => setWritten(e.target.value)}
              />
              <label htmlFor="code">Code</label>
              <textarea id="code" value={code} onChange={(e) => setCode(e.target.value)} />
              <div className="actions">
                <button type="button" className="secondary" onClick={() => setStep(2)}>
                  Back to brief
                </button>
                <button type="button" onClick={startDefense} disabled={!!busy}>
                  Continue to defense
                </button>
              </div>
            </>
          )}

          {step === 4 && (
            <>
              <h2>Defense questions</h2>
              <p className="lede">These target the weakest parts of what you submitted.</p>
              {questions.map((question, i) => (
                <div className="qa" key={question}>
                  <p>
                    <strong>
                      Question {i + 1} of {questions.length}
                    </strong>
                  </p>
                  <p>{question}</p>
                  <textarea
                    value={answers[i] || ""}
                    onChange={(e) =>
                      setAnswers((current) =>
                        current.map((item, idx) => (idx === i ? e.target.value : item)),
                      )
                    }
                  />
                </div>
              ))}
              <div className="actions">
                <button type="button" className="secondary" onClick={() => setStep(3)}>
                  Back
                </button>
                <button type="button" onClick={runScoring} disabled={!!busy}>
                  Score this attempt
                </button>
              </div>
            </>
          )}

          {step === 5 && (
            <>
              <h2>Scoring in progress</h2>
              <p className="lede">{status || "Please wait. Two independent assessor passes can take a couple of minutes."}</p>
            </>
          )}

          {step === 6 && (
            <>
              <h2>Scored report</h2>
              <p className="lede">{verdict}</p>
              <div className="actions">
                <button type="button" onClick={downloadHtml}>
                  Download HTML
                </button>
                {githubUrl ? (
                  <a className="btn secondary" href={githubUrl} target="_blank" rel="noreferrer">
                    JSON on GitHub
                  </a>
                ) : null}
                {htmlUrl ? (
                  <a className="btn secondary" href={htmlUrl} target="_blank" rel="noreferrer">
                    HTML on GitHub
                  </a>
                ) : null}
              </div>
              {html ? (
                <iframe
                  title="CAPE HTML report"
                  srcDoc={html}
                  style={{ width: "100%", minHeight: 720, marginTop: 18, border: "1px solid #e2d9c6" }}
                />
              ) : null}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
