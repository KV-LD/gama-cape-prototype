import { DEFAULT_REPO } from "./constants";
import { githubToken } from "./llm";
import { renderReport } from "./report";
import type { AttemptRecord } from "./types";

function slug(text: string): string {
  const cleaned = (text || "candidate").replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  return (cleaned.slice(0, 80) || "candidate");
}

async function putFile(repo: string, path: string, content: string, message: string, sha?: string) {
  const token = githubToken();
  const payload: Record<string, unknown> = {
    message,
    content: Buffer.from(content, "utf8").toString("base64"),
    branch: process.env.GITHUB_ATTEMPTS_BRANCH || "main",
  };
  if (sha) payload.sha = sha;
  const resp = await fetch(`https://api.github.com/repos/${repo}/contents/${path}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "gama-cape-prototype",
    },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const details = (await resp.text()).slice(0, 400);
    throw new Error(
      `GitHub would not save ${path} (HTTP ${resp.status}). Check GITHUB_TOKEN repo permissions. Details: ${details}`,
    );
  }
  return (await resp.json()) as {
    content?: { html_url?: string; sha?: string };
    html_url?: string;
    sha?: string;
  };
}

function contentUrl(
  data: { content?: { html_url?: string }; html_url?: string },
  repo: string,
  path: string,
): string {
  return (
    data.content?.html_url ||
    data.html_url ||
    `https://github.com/${repo}/blob/${process.env.GITHUB_ATTEMPTS_BRANCH || "main"}/${path}`
  );
}

export async function commitAttempt(record: AttemptRecord): Promise<{
  github_url: string;
  html_report_url: string;
}> {
  const repo = process.env.GITHUB_REPO || DEFAULT_REPO;
  const now = new Date();
  const timestamp = now.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
  const isoTime = now.toISOString().replace(/\.\d{3}Z$/, "Z");
  const candidate = slug(String(record.candidate_name || "candidate"));
  const moduleId = record.module_id ?? "x";
  const folder = `attempts/${candidate}_${moduleId}_${timestamp}`;
  const jsonPath = `${folder}/record.json`;
  const htmlPath = `${folder}/report.html`;

  record.recorded_at = record.recorded_at || isoTime;
  const verdict = record.verdict || record.score_sheet?.verdict || "UNKNOWN";
  const message = `CAPE attempt: ${record.candidate_name} - Module ${moduleId} (${record.module_name}) - ${verdict}`;

  const jsonResp = await putFile(repo, jsonPath, JSON.stringify(record, null, 2), message);
  const githubUrl = contentUrl(jsonResp, repo, jsonPath);
  record.github_url = githubUrl;

  const htmlDoc = renderReport(record);
  const htmlResp = await putFile(repo, htmlPath, htmlDoc, `${message} (HTML report)`);
  const htmlReportUrl = contentUrl(htmlResp, repo, htmlPath);
  record.html_report_url = htmlReportUrl;

  const sha = jsonResp.content?.sha || jsonResp.sha;
  await putFile(repo, jsonPath, JSON.stringify(record, null, 2), `${message} (audit URLs)`, sha);

  return { github_url: githubUrl, html_report_url: htmlReportUrl };
}
