"""Generate a Manning liveProject-style capstone problem statement via Grok."""

from __future__ import annotations

from typing import Any

from llm import GROK_MODEL, chat, get_module


SLOT_INSTRUCTIONS = """
You are writing a Manning liveProject-style capstone brief for an FDE trainee.

Tone: a real staged project brief for a working professional — not a puzzle, not an exam question, not academic homework.

You MUST use this exact section structure and no other top-level sections:

1. Business Context
   A realistic company/scenario in the given domain. 2-3 sentences.

2. Explicit Constraints
   3-4 concrete constraints (data limits, timeline, compliance, tooling).
   Naturally reference the candidate's chosen tools and hyperscaler when provided.

3. Deliverable Spec
   Precisely what artifact(s) the candidate must produce.
   Tie every deliverable directly to the module skill indices so the work generates evidence for EACH skill index listed.

4. One Deliberate Complication
   Exactly one realistic curveball (ambiguous requirement, conflicting stakeholder ask, or a constraint that changes partway). Not a laundry list.

Do not add extra sections. Do not ask questions back. Output only the problem statement.
""".strip()


def build_capstone_prompt(
    module: dict,
    domain: str,
    tools: list[str],
    hyperscaler: str | None,
) -> str:
    skills = []
    for idx in module.get("skill_indices") or []:
        skills.append(f"- {idx['name']}: {idx['observable_behaviour']}")
    tools_text = ", ".join(tools) if tools else "none specified"
    cloud_text = hyperscaler if hyperscaler else "None (no hyperscaler required)"
    return f"""{SLOT_INSTRUCTIONS}

MODULE
- id: {module['id']}
- name: {module['name']}
- phase_ref: {module['phase_ref']}

SKILL INDICES (every one must be exercisable by the deliverable spec)
{chr(10).join(skills)}

CANDIDATE CHOICES
- domain: {domain}
- AI tools used: {tools_text}
- hyperscaler: {cloud_text}
"""


def generate_capstone_bundle(
    module_id: int,
    domain: str,
    tools: list[str],
    hyperscaler: str | None,
) -> dict[str, Any]:
    module = get_module(module_id)
    prompt = build_capstone_prompt(module, domain, tools, hyperscaler)
    statement = chat(
        [
            {
                "role": "system",
                "content": (
                    "You write Manning liveProject briefs. Follow the user's slot "
                    "template exactly. Do not freelance extra sections."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=2500,
    )
    return {
        "problem_statement": statement.strip(),
        "prompt": prompt,
        "model": GROK_MODEL,
        "module": module,
    }


def generate_capstone(
    module_id: int,
    domain: str,
    tools: list[str],
    hyperscaler: str | None,
) -> str:
    return generate_capstone_bundle(module_id, domain, tools, hyperscaler)["problem_statement"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate one CAPE capstone brief.")
    parser.add_argument("--module", type=int, required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--tools", default="Claude,Cursor")
    parser.add_argument("--hyperscaler", default=None)
    args = parser.parse_args()
    tools = [t.strip() for t in args.tools.split(",") if t.strip()]
    print(generate_capstone(args.module, args.domain, tools, args.hyperscaler))
