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

DEFAULT_REPO = "KV-LD/gama-cape-prototype"


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text or "candidate").strip("_")
    return cleaned[:80] or "candidate"


def commit_attempt(record: dict[str, Any], repo: str = DEFAULT_REPO) -> str:
    repo = os.getenv("GITHUB_REPO", repo)
    token = github_token()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = _slug(str(record.get("candidate_name") or "candidate"))
    module_id = record.get("module_id") or record.get("module", {}).get("id") or "x"
    path = f"attempts/{candidate}_{module_id}_{timestamp}/record.json"

    verdict = record.get("verdict") or (record.get("score_sheet") or {}).get("verdict") or "UNKNOWN"
    module_name = record.get("module_name") or ""
    message = f"CAPE attempt: {record.get('candidate_name')} - Module {module_id} ({module_name}) - {verdict}"

    body_json = json.dumps(record, indent=2, ensure_ascii=False)
    encoded = base64.b64encode(body_json.encode("utf-8")).decode("ascii")

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
            f"GitHub would not save the attempt (HTTP {resp.status_code}). "
            f"GITHUB_TOKEN found but cannot write to {repo} — check the token's repo permissions. "
            f"Details: {resp.text[:400]}"
        )
    data = resp.json()
    html_url = (data.get("content") or {}).get("html_url") or data.get("html_url")
    if not html_url:
        html_url = f"https://github.com/{repo}/blob/main/{path}"
    return html_url
