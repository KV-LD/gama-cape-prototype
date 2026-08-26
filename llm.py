"""Shared OpenRouter REST helper. No SDK — plain requests only."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Verified against GET https://openrouter.ai/api/v1/models (do not guess).
GROK_MODEL = "x-ai/grok-4.5"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
ALLOWED_SCORES = {0, 25, 50, 75, 100}


def load_json(rel_path: str) -> dict:
    with open(ROOT / rel_path, encoding="utf-8") as fh:
        return json.load(fh)


def load_rubric() -> dict:
    return load_json("config/rubric_config.json")


def load_vector() -> dict:
    return load_json("config/vector_config.json")


def get_module(module_id: int) -> dict:
    rubric = load_rubric()
    for module in rubric["modules"]:
        if module["id"] == int(module_id):
            return module
    raise ValueError(f"Unknown module id: {module_id}. Valid ids are 1 through 9.")


def mapped_vector_codes(module: dict) -> list[str]:
    if module.get("vector_blend") == "all_six" or module.get("id") == 9:
        return ["V", "E", "C", "T", "O", "R"]
    primary = module.get("vector_primary")
    secondary = module.get("vector_secondary")
    codes = []
    if primary:
        codes.append(primary)
    if secondary and secondary not in codes:
        codes.append(secondary)
    return codes


def openrouter_key() -> str:
    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Copy .env.example to .env and paste your key, "
            "then rerun python check_env.py."
        )
    return key


def github_token() -> str:
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is missing. Copy .env.example to .env and paste your token, "
            "then rerun python check_env.py."
        )
    return token


def chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.4,
    json_object: bool = False,
    max_tokens: int = 4000,
) -> str:
    headers = {
        "Authorization": f"Bearer {openrouter_key()}",
        "Content-Type": "application/json",
        "User-Agent": "gama-cape-prototype",
        "HTTP-Referer": "https://github.com/KV-LD/gama-cape-prototype",
        "X-Title": "GAMA CAPE",
    }
    body: dict[str, Any] = {
        "model": GROK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_object:
        body["response_format"] = {"type": "json_object"}

    resp = requests.post(OPENROUTER_CHAT_URL, headers=headers, json=body, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(
            f"OpenRouter chat failed (HTTP {resp.status_code}). "
            f"Details: {resp.text[:400]}"
        )
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected OpenRouter response: {data}") from exc


def extract_json(text: str) -> Any:
    """Parse JSON from a model reply, including fenced ```json blocks."""
    stripped = (text or "").strip()
    if not stripped:
        raise ValueError("Empty model reply; cannot parse JSON.")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if fence:
        return json.loads(fence.group(1).strip())
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(stripped[start : end + 1])
    raise ValueError(f"Could not find JSON in model reply: {stripped[:240]}")


def clamp_score(value: Any) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    nearest = min(ALLOWED_SCORES, key=lambda s: abs(s - number))
    return nearest
