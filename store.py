"""Commit a full CAPE attempt record to GitHub as the audit trail."""

from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import requests

from llm import github_token
from report import render_report

DEFAULT_REPO = "KV-LD/gama-cape-prototype"


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text or "candidate").strip("_")
    return cleaned[:80] or "candidate"


def _put_file(
    *,
    repo: str,
    path: str,
    content: str,
    message: str,
    token: str,
) -> dict[str, Any]:
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gama-cape-prototype",
    }
    payload = {
        "message": message,
        "content": encoded,
        "branch": os.getenv("GITHUB_ATTEMPTS_BRANCH", "main"),
    }
    resp = requests.put(url, headers=headers, json=payload, timeout=60)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"GitHub would not save {path} (HTTP {resp.status_code}). "
            f"GITHUB_TOKEN found but cannot write to {repo} — check the token's repo permissions. "
            f"Details: {resp.text[:400]}"
        )
    return resp.json()


def _content_html_url(data: dict[str, Any], repo: str, path: str) -> str:
    html_url = (data.get("content") or {}).get("html_url") or data.get("html_url")
    if html_url:
        return html_url
    branch = os.getenv("GITHUB_ATTEMPTS_BRANCH", "main")
    return f"https://github.com/{repo}/blob/{branch}/{path}"


def commit_attempt(record: dict[str, Any], repo: str = DEFAULT_REPO) -> str:
    repo = os.getenv("GITHUB_REPO", repo)
    token = github_token()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    iso_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    candidate = _slug(str(record.get("candidate_name") or "candidate"))
    module_id = record.get("module_id") or record.get("module", {}).get("id") or "x"
    folder = f"attempts/{candidate}_{module_id}_{timestamp}"
    json_path = f"{folder}/record.json"
    html_path = f"{folder}/report.html"

    record = dict(record)
    record.setdefault("recorded_at", iso_time)

    verdict = record.get("verdict") or (record.get("score_sheet") or {}).get("verdict") or "UNKNOWN"
    module_name = record.get("module_name") or ""
    message = f"CAPE attempt: {record.get('candidate_name')} - Module {module_id} ({module_name}) - {verdict}"

    body_json = json.dumps(record, indent=2, ensure_ascii=False)
    json_resp = _put_file(repo=repo, path=json_path, content=body_json, message=message, token=token)
    github_url = _content_html_url(json_resp, repo, json_path)

    record["github_url"] = github_url
    html_doc = render_report(record)
    html_resp = _put_file(
        repo=repo,
        path=html_path,
        content=html_doc,
        message=f"{message} (HTML report)",
        token=token,
    )
    html_report_url = _content_html_url(html_resp, repo, html_path)

    # Refresh JSON so the stored record includes both URLs.
    record["html_report_url"] = html_report_url
    body_json = json.dumps(record, indent=2, ensure_ascii=False)
    sha = ((json_resp.get("content") or {}).get("sha")) or json_resp.get("sha")
    url = f"https://api.github.com/repos/{repo}/contents/{json_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gama-cape-prototype",
    }
    encoded = base64.b64encode(body_json.encode("utf-8")).decode("ascii")
    payload = {
        "message": f"{message} (audit URLs)",
        "content": encoded,
        "branch": os.getenv("GITHUB_ATTEMPTS_BRANCH", "main"),
        "sha": sha,
    }
    resp = requests.put(url, headers=headers, json=payload, timeout=60)
    if resp.status_code not in (200, 201):
        return {"github_url": github_url, "html_report_url": html_report_url}
    return {"github_url": github_url, "html_report_url": html_report_url}
