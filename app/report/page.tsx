"use client";

import { useState } from "react";
import { postJson } from "@/lib/clientFetch";

export default function ReportPage() {
  const [raw, setRaw] = useState("");
  const [html, setHtml] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function convert(record: unknown) {
    setBusy(true);
    setError("");
    try {
      const data = await postJson<{ html?: string }>("/api/render-report", record);
      if (!data.html) throw new Error("Could not convert that JSON.");
      setHtml(data.html);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not convert that JSON.");
    } finally {
      setBusy(false);
    }
  }

  async function fromPaste() {
    try {
      const parsed = JSON.parse(raw);
      await convert(parsed);
    } catch {
      setError("That is not valid JSON. Paste the full record.json file.");
    }
  }

  function fromFile(file: File | null) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const parsed = JSON.parse(String(reader.result));
        setRaw(JSON.stringify(parsed, null, 2));
        await convert(parsed);
      } catch {
        setError("That file is not valid JSON.");
      }
    };
    reader.readAsText(file);
  }

  function downloadHtml() {
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "cape-report.html";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="shell">
      <header className="brand">
        <div>
          <p>G.A.Menon Academy</p>
          <h1>Convert a saved JSON record to HTML</h1>
        </div>
        <nav>
          <a href="/">Assessment</a>
          <a href="/report">JSON → HTML</a>
        </nav>
      </header>
      <section className="card">
        <p className="lede">
          Yes. Every attempt saved under <code>attempts/</code> is a complete record. Paste
          or upload <code>record.json</code> to get a printable HTML document with scores,
          evidence, the capstone, your submission, and defense answers.
        </p>
        {error ? <div className="error">{error}</div> : null}
        <label htmlFor="file">Upload record.json</label>
        <input
          id="file"
          type="file"
          accept="application/json,.json"
          onChange={(e) => fromFile(e.target.files?.[0] || null)}
        />
        <label htmlFor="json">Or paste JSON</label>
        <textarea id="json" value={raw} onChange={(e) => setRaw(e.target.value)} />
        <div className="actions">
          <button type="button" onClick={fromPaste} disabled={busy}>
            Convert to HTML
          </button>
          {html ? (
            <button type="button" className="secondary" onClick={downloadHtml}>
              Download HTML
            </button>
          ) : null}
        </div>
        {html ? (
          <iframe
            title="Converted CAPE report"
            srcDoc={html}
            style={{ width: "100%", minHeight: 720, marginTop: 18, border: "1px solid #e2d9c6" }}
          />
        ) : null}
      </section>
    </div>
  );
}
