#!/usr/bin/env python3
"""Step 0 — Environment check for GAMA CAPE.

Confirms the two secrets exist and actually work:
  - OPENROUTER_API_KEY  (can talk to OpenRouter)
  - GITHUB_TOKEN        (can see the private prototype repo)

Run:  python check_env.py
"""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

REPO = os.getenv("GITHUB_REPO", "KV-LD/gama-cape-prototype")
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
GITHUB_REPO_URL = f"https://api.github.com/repos/{REPO}"


def _present(value: str | None) -> bool:
    return bool(value and value.strip() and "your_key_here" not in value and "your_token_here" not in value)


def main() -> int:
    load_dotenv()

    print("=" * 60)
    print("GAMA CAPE — environment check")
    print("=" * 60)
    print()

    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.isfile(env_file):
        print("Found a .env file in this folder. Good.")
    else:
        print("No .env file found in this folder.")
        print("  That is OK if the keys are already set as environment variables,")
        print("  but most people should copy .env.example to .env and paste their keys.")
    print()

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    failures = 0

    # --- key presence ---
    if _present(openrouter_key):
        print("PASS  OPENROUTER_API_KEY is present and not empty.")
    else:
        failures += 1
        print("FAIL  OPENROUTER_API_KEY is missing or empty.")
        print("      Fix: open the .env file and set")
        print("      OPENROUTER_API_KEY=... using a key from https://openrouter.ai/keys")
        print("      Do not leave the placeholder your_key_here.")

    if _present(github_token):
        print("PASS  GITHUB_TOKEN is present and not empty.")
    else:
        failures += 1
        print("FAIL  GITHUB_TOKEN is missing or empty.")
        print("      Fix: open the .env file and set")
        print("      GITHUB_TOKEN=... using a GitHub personal access token")
        print("      that can read and write this private repo.")
        print("      Create one at https://github.com/settings/tokens")
        print("      (classic token needs 'repo' scope).")

    print()

    # --- OpenRouter live call ---
    print("Checking OpenRouter (this should take a second)...")
    if _present(openrouter_key):
        try:
            resp = requests.get(
                OPENROUTER_MODELS_URL,
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "User-Agent": "gama-cape-check-env",
                },
                timeout=30,
            )
            if resp.status_code == 200:
                payload = resp.json()
                models = payload.get("data") or []
                print(f"PASS  OpenRouter accepted the key (saw {len(models)} models).")
            elif resp.status_code in (401, 403):
                failures += 1
                print("FAIL  OPENROUTER_API_KEY was found but OpenRouter rejected it.")
                print("      Fix: copy a fresh key from https://openrouter.ai/keys")
                print("      and replace the value in .env (no extra spaces or quotes).")
            else:
                failures += 1
                print(f"FAIL  OpenRouter returned HTTP {resp.status_code}.")
                print(f"      Details: {resp.text[:300]}")
                print("      Fix: check your internet connection and try again.")
        except requests.RequestException as exc:
            failures += 1
            print("FAIL  Could not reach OpenRouter.")
            print(f"      Details: {exc}")
            print("      Fix: check your internet connection, then rerun this script.")
    else:
        print("SKIP  OpenRouter live check (no key to try).")

    print()

    # --- GitHub live call ---
    print(f"Checking GitHub access to {REPO}...")
    if _present(github_token):
        try:
            resp = requests.get(
                GITHUB_REPO_URL,
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "gama-cape-check-env",
                },
                timeout=30,
            )
            if resp.status_code == 200:
                name = (resp.json() or {}).get("full_name", REPO)
                print(f"PASS  GITHUB_TOKEN can see the repo {name}.")
            elif resp.status_code == 401:
                failures += 1
                print("FAIL  GITHUB_TOKEN was found but GitHub says it is invalid.")
                print("      Fix: create a new token and paste it into .env.")
            elif resp.status_code == 404:
                failures += 1
                print(
                    f"FAIL  GITHUB_TOKEN found but cannot access {REPO} — "
                    "check the token's repo permissions."
                )
                print("      The token must be allowed to see this private repository.")
                print("      If you used a fine-grained token, add KV-LD/gama-cape-prototype")
                print("      under Repository access, with Contents: Read and write.")
            elif resp.status_code == 403:
                failures += 1
                print("FAIL  GITHUB_TOKEN found but GitHub refused access (403).")
                print(f"      Check the token's repo permissions for {REPO}.")
            else:
                failures += 1
                print(f"FAIL  GitHub returned HTTP {resp.status_code}.")
                print(f"      Details: {resp.text[:300]}")
        except requests.RequestException as exc:
            failures += 1
            print("FAIL  Could not reach GitHub.")
            print(f"      Details: {exc}")
            print("      Fix: check your internet connection, then rerun this script.")
    else:
        print("SKIP  GitHub live check (no token to try).")

    print()
    print("=" * 60)
    if failures:
        print(f"RESULT: {failures} check(s) failed. Do not run the prototype yet.")
        print("Fix the FAIL lines above, save .env, then run:  python check_env.py")
        print("=" * 60)
        return 1

    print("RESULT: All checks passed. You can run:  python main.py")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
