#!/usr/bin/env python3
"""Step 9 — end-to-end self-test of the CAPE pipeline (no interactive typing)."""

from __future__ import annotations

import json
import sys

from generate_capstone import generate_capstone_bundle
from llm import get_module, load_rubric, load_vector, mapped_vector_codes
from main import run_pipeline
from scorer import determine_verdict, reconcile_pair


FAKE_WRITTEN = """
RetailCo is a mid-size fashion retailer. I treated 'personalize the homepage' as the stated brief
and reframed it as: reduce homepage bounce for first-time mobile visitors without increasing
returns. I argued this is an AI ranking problem, not a rule-based merchandising calendar,
because intent signals (session, weather, inventory) change faster than a static ruleset.

Responsible AI: I flagged popularity-bias toward already-bestselling SKUs which would starve
new/plus-size inventory. Mitigation: diversity constraint in the ranker (max 40% of slots from
top-decile SKUs) and a weekly fairness report by size band.

Prompt library (partial):
System: You are a merchandiser. Instruction: propose 3 homepage stories.
Context: inventory snapshot, campaign calendar.
Constraints: no medical claims; refuse if size data missing.
I tested an edge case where size metadata was null; the prompt then asked for a human merchandiser.

Gap: I did not run a full prompt-eval harness beyond that one null-metadata case.
I also did not include a stakeholder interview transcript.
"""

FAKE_CODE = """
# toy ranker sketch used with Claude + Cursor
def diversity_cap(items, cap=0.4):
    top = [i for i in items if i['decile'] == 10]
    limited = top[: int(len(items) * cap)]
    rest = [i for i in items if i not in limited]
    return limited + rest

PROMPTS = {
  "homepage": {
    "instruction": "propose 3 homepage stories",
    "context": "{inventory} {calendar}",
    "constraints": "no medical claims; escalate if size data missing"
  }
}
"""

FAKE_DEFENSE_ANSWERS = [
    "I only tested the null size-metadata path once; I do not have a regression set of 20 cases.",
    "I did not capture a buyer-side interview. I inferred the bounce problem from analytics only.",
    "The 40% cap is a heuristic, not validated against return-rate lift.",
]


def test_verdict_math() -> None:
    print("Self-test A: blend / disagreement / verdict math (no LLM)")
    r = reconcile_pair(50, 75, threshold=25)
    assert r["borderline_review"] is False and r["final"] == 62.5, r
    r = reconcile_pair(25, 75, threshold=25)
    assert r["borderline_review"] is True and r["final"] == 25 and r["method"] == "lower_placeholder_not_averaged", r

    assert determine_verdict(80, True, False).startswith("BORDERLINE")
    assert determine_verdict(80, False, False) == "EXEMPTED"
    assert determine_verdict(80, False, True) == "COMPLETION PASS — TRAINING RECOMMENDED, NOT EXEMPTED"
    assert determine_verdict(60, False, False) == "COMPLETION PASS — TRAINING RECOMMENDED, NOT EXEMPTED"
    assert determine_verdict(40, False, False) == "FAIL — FULL TRAINING REQUIRED"

    # 60/40 blend sanity
    blended = 70 * 0.6 + 50 * 0.4
    assert abs(blended - 62.0) < 1e-9
    print("  PASS  disagreement uses lower score, not average")
    print("  PASS  borderline overrides exemption")
    print("  PASS  floor violation blocks exemption")
    print("  PASS  60/40 blend arithmetic")


def test_full_pipeline() -> dict:
    print()
    print("Self-test B: full pipeline (retail / module 1 / Claude+Cursor)")
    module = get_module(1)
    vector_config = load_vector()
    print("  Generating capstone...")
    bundle = generate_capstone_bundle(1, "retail", ["Claude", "Cursor"], None)
    statement = bundle["problem_statement"].lower()
    if "retail" not in statement:
        raise AssertionError("Problem statement did not reference the retail domain.")
    joined_tools = statement + bundle["prompt"].lower()
    if "claude" not in joined_tools.lower() and "cursor" not in joined_tools.lower():
        raise AssertionError("Problem statement/prompt did not reference the chosen tools.")
    print("  PASS  problem statement generated and references domain/tools")

    intake = {
        "candidate_name": "Dummy Selftest",
        "domain": "retail",
        "module_id": 1,
        "module_name": module["name"],
        "module_config": module,
        "tools": ["Claude", "Cursor"],
        "hyperscaler": None,
        "problem_statement": bundle["problem_statement"],
        "generation_prompt": bundle["prompt"],
        "generation_model": bundle["model"],
        "submission": {
            "written": FAKE_WRITTEN.strip(),
            "code": FAKE_CODE.strip(),
            "text": FAKE_WRITTEN.strip() + "\n\n--- CODE ---\n\n" + FAKE_CODE.strip(),
        },
    }

    record = run_pipeline(intake=intake, defense_answers=FAKE_DEFENSE_ANSWERS)
    qa = record["defense_qa"]
    if not (2 <= len(qa) <= 3):
        raise AssertionError(f"Expected 2-3 defense questions, got {len(qa)}")
    blob = " ".join(q["question"].lower() for q in qa)
    if "homepage" not in blob and "prompt" not in blob and "bias" not in blob and "size" not in blob:
        print("  WARN  defense questions may be weakly grounded; continuing.")
    else:
        print("  PASS  defense questions generated against the fake submission")

    sheet = record["score_sheet"]
    for label, payload in (("A", sheet["pass_a"]), ("B", sheet["pass_b"])):
        if set(payload["skill_scores"]) != {s["name"] for s in module["skill_indices"]}:
            raise AssertionError(f"Assessor {label} missed a skill index")
        if set(payload["vector_scores"]) != set(mapped_vector_codes(module)):
            raise AssertionError(f"Assessor {label} missed a VECTOR dimension")
    print("  PASS  both scoring passes returned valid JSON covering skills + VECTOR")

    expected = round(sheet["module_score"] * 0.6 + sheet["vector_score"] * 0.4, 2)
    if abs(expected - sheet["final_blended_score"]) > 0.05:
        raise AssertionError(f"Blend math mismatch: {expected} vs {sheet['final_blended_score']}")
    print(f"  PASS  blend math {sheet['module_score']}*0.6 + {sheet['vector_score']}*0.4 = {sheet['final_blended_score']}")

    allowed = {
        "BORDERLINE — HUMAN REVIEW REQUIRED",
        "EXEMPTED",
        "COMPLETION PASS — TRAINING RECOMMENDED, NOT EXEMPTED",
        "FAIL — FULL TRAINING REQUIRED",
    }
    if sheet["verdict"] not in allowed:
        raise AssertionError(f"Unexpected verdict: {sheet['verdict']}")
    recomputed = determine_verdict(
        sheet["final_blended_score"],
        sheet["borderline_review"],
        sheet["floor_violation"],
        exemption_pass=load_rubric()["cutoffs"]["exemption_pass"],
        completion_pass=load_rubric()["cutoffs"]["completion_pass"],
    )
    if recomputed != sheet["verdict"]:
        raise AssertionError(f"Verdict logic mismatch: {sheet['verdict']} vs {recomputed}")
    print(f"  PASS  verdict logic: {sheet['verdict']}")

    if "attempts/" not in (record.get("github_url") or ""):
        raise AssertionError(f"GitHub URL missing attempts/ path: {record.get('github_url')}")
    print(f"  PASS  record committed: {record['github_url']}")
    return record


def main() -> int:
    print("=" * 72)
    print("GAMA CAPE — Step 9 self-test")
    print("=" * 72)
    test_verdict_math()
    record = test_full_pipeline()
    print()
    print("SELF-TEST COMPLETE")
    print(json.dumps({
        "verdict": record["verdict"],
        "blended": record["score_sheet"]["final_blended_score"],
        "github_url": record["github_url"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
