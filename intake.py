"""Plain-English CLI intake for a non-coder candidate."""

from __future__ import annotations

import os
from typing import Any

from generate_capstone import generate_capstone_bundle
from llm import load_rubric

DOMAINS = [
    "healthcare",
    "retail",
    "bfsi",
    "manufacturing",
    "supply chain",
    "automotive",
]

AI_TOOLS = ["Claude", "Copilot", "Gemini", "Cursor", "Devin"]
HYPERSCALERS = ["AWS", "Azure", "GCP", "None"]


def _ask(prompt: str) -> str:
    return input(prompt).strip()


def _pick_from_menu(title: str, options: list[str], allow_none: bool = False) -> str:
    print()
    print(title)
    for i, option in enumerate(options, start=1):
        print(f"  {i}. {option}")
    while True:
        raw = _ask("Type the number of your choice and press Enter: ")
        try:
            idx = int(raw)
        except ValueError:
            print("Please type a number from the list, then press Enter.")
            continue
        if 1 <= idx <= len(options):
            chosen = options[idx - 1]
            if allow_none and chosen == "None":
                return ""
            return chosen
        print("That number is not on the list. Try again.")


def _pick_tools() -> list[str]:
    print()
    print("Which AI tools did you use on this work? You can pick more than one.")
    for i, tool in enumerate(AI_TOOLS, start=1):
        print(f"  {i}. {tool}")
    print("Type the numbers separated by commas. Example: 1,4")
    while True:
        raw = _ask("Your tools: ")
        parts = [p.strip() for p in raw.replace(" ", ",").split(",") if p.strip()]
        chosen: list[str] = []
        ok = True
        for part in parts:
            try:
                idx = int(part)
            except ValueError:
                print("Please use numbers only, like 1,4")
                ok = False
                break
            if not 1 <= idx <= len(AI_TOOLS):
                print(f"{idx} is not on the list. Try again.")
                ok = False
                break
            name = AI_TOOLS[idx - 1]
            if name not in chosen:
                chosen.append(name)
        if ok and chosen:
            return chosen
        if ok and not chosen:
            print("Pick at least one tool.")


def _read_multiline_or_file(kind: str) -> str:
    print()
    print(f"Paste your {kind} now.")
    print("When you are finished, type END on its own line and press Enter.")
    print("Or, instead of pasting, type a file path (for example notes.txt) and press Enter.")
    first = input("> ")
    candidate = first.strip()
    if candidate and os.path.isfile(candidate):
        with open(candidate, encoding="utf-8") as fh:
            return fh.read()
    lines = [first]
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def collect_profile() -> dict[str, Any]:
    print()
    print("Welcome to GAMA CAPE (Capability Assessment & Proficiency Engine).")
    print("This will take a few minutes. Answer each question, then press Enter.")
    print()

    while True:
        name = _ask("What is your name? ")
        if name:
            break
        print("Please type your name so we can save your attempt.")

    domain = _pick_from_menu("Which industry domain is this work for?", DOMAINS)

    rubric = load_rubric()
    modules = rubric["modules"]
    print()
    print("Which FDE module are you submitting for?")
    for module in modules:
        extra = ""
        if not module.get("exemptible", True):
            extra = "  (not exemptible — everyone still completes this)"
        print(f"  {module['id']}. {module['name']}{extra}")
    while True:
        raw = _ask("Type the module number (1-9) and press Enter: ")
        try:
            module_id = int(raw)
        except ValueError:
            print("Please type a number from 1 to 9.")
            continue
        match = next((m for m in modules if m["id"] == module_id), None)
        if match:
            break
        print("That is not a valid module number. Try again.")

    tools = _pick_tools()
    hyperscaler = _pick_from_menu(
        "Which cloud (hyperscaler) did you use? Pick None if you did not use one.",
        HYPERSCALERS,
        allow_none=True,
    ) or None

    return {
        "candidate_name": name,
        "domain": domain,
        "module_id": match["id"],
        "module_name": match["name"],
        "module_config": match,
        "tools": tools,
        "hyperscaler": hyperscaler,
    }


def collect_submission() -> dict[str, str]:
    written = _read_multiline_or_file("written notes / architecture docs")
    code = _read_multiline_or_file("code")
    return {
        "written": written,
        "code": code,
        "text": (written + "\n\n--- CODE ---\n\n" + code).strip(),
    }


def run_intake() -> dict[str, Any]:
    profile = collect_profile()
    print()
    print("Generating a fresh capstone problem for you. This can take up to a minute...")
    bundle = generate_capstone_bundle(
        profile["module_id"],
        profile["domain"],
        profile["tools"],
        profile["hyperscaler"],
    )
    print()
    print("=" * 72)
    print("YOUR CAPSTONE PROBLEM")
    print("=" * 72)
    print(bundle["problem_statement"])
    print("=" * 72)
    print()
    print("Complete this offline if you want, then come back and paste your work.")
    submission = collect_submission()
    return {
        **profile,
        "problem_statement": bundle["problem_statement"],
        "generation_prompt": bundle["prompt"],
        "generation_model": bundle["model"],
        "submission": submission,
    }
