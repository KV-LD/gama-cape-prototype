"""Two-pass Grok scoring against FDE module rubric + VECTOR evidence rubric."""

from __future__ import annotations

from typing import Any

from llm import (
    ALLOWED_SCORES,
    chat,
    clamp_score,
    extract_json,
    mapped_vector_codes,
)


def _skill_names(module_config: dict) -> list[str]:
    return [s["name"] for s in module_config.get("skill_indices") or []]


def score_pass(
    module_config: dict,
    vector_config: dict,
    submission: dict,
    defense_qa: list[dict[str, str]],
    pass_label: str,
) -> dict:
    skill_names = _skill_names(module_config)
    vector_codes = mapped_vector_codes(module_config)
    skill_lines = []
    for idx in module_config.get("skill_indices") or []:
        skill_lines.append(f"- {idx['name']}: {idx['observable_behaviour']}")

    vec_lines = []
    mapping = vector_config["score_band_mapping"]
    for code in vector_codes:
        dim = vector_config["dimensions"][code]
        levels = dim["levels"]
        vec_lines.append(f"{code} {dim['name']}: {dim['definition']}")
        vec_lines.append(f"  1 Emerging -> {mapping['1_Emerging']}: {levels['1']}")
        vec_lines.append(f"  2 Developing -> {mapping['2_Developing']}: {levels['2']}")
        vec_lines.append(f"  3 Established -> {mapping['3_Established']}: {levels['3']}")
        vec_lines.append(f"  4 Advanced -> {mapping['4_Advanced']}: {levels['4']}")
        vec_lines.append(f"  5 Defining -> {mapping['5_Defining']}: {levels['5']}")

    qa_lines = []
    for pair in defense_qa:
        qa_lines.append(f"Q: {pair.get('question', '')}")
        qa_lines.append(f"A: {pair.get('answer', '')}")

    written = submission.get("text") or submission.get("written") or ""
    code = submission.get("code") or ""

    user = f"""You are {pass_label}, an independent assessor. Do not coordinate with any other assessor.
Score ONLY from evidence in the submission and defense answers. If a skill index is not evidenced, score 0.
Do NOT invent praise. Do NOT infer competence that is not shown.

Allowed numeric scores only: 0, 25, 50, 75, 100.
FDE scale: Not Evidenced=0, Below Expectations=25, Meets Expectations=50, Above Average Can Improve=75, Complete & Clear=100.
VECTOR levels map 1:1 onto that same number line.

MODULE: {module_config['id']} {module_config['name']}

SKILL INDICES TO SCORE (every one)
{chr(10).join(skill_lines)}

VECTOR DIMENSIONS TO SCORE (every one listed)
{chr(10).join(vec_lines)}

SUBMISSION (written)
{written}

SUBMISSION (code)
{code}

DEFENSE Q&A
{chr(10).join(qa_lines)}

Return STRICT JSON only with this shape:
{{
  "skill_scores": {{ {', '.join(f'"{n}": <0|25|50|75|100>' for n in skill_names)} }},
  "vector_scores": {{ {', '.join(f'"{c}": <0|25|50|75|100>' for c in vector_codes)} }},
  "evidence": {{
    "<skill or vector code>": "cite the specific sentence/artefact (or state ABSENT)"
  }}
}}
"""
    raw = chat(
        [
            {
                "role": "system",
                "content": (
                    f"You are {pass_label}. Independent evidence-based assessor. "
                    "JSON only. Score 0 when evidence is absent. Never invent work product."
                ),
            },
            {"role": "user", "content": user},
        ],
        temperature=0.35,
        json_object=True,
        max_tokens=3500,
    )
    parsed = extract_json(raw)
    skill_scores = {}
    for name in skill_names:
        skill_scores[name] = clamp_score((parsed.get("skill_scores") or {}).get(name, 0))
    vector_scores = {}
    for code in vector_codes:
        vector_scores[code] = clamp_score((parsed.get("vector_scores") or {}).get(code, 0))
    evidence = parsed.get("evidence") or {}
    return {
        "pass_label": pass_label,
        "skill_scores": skill_scores,
        "vector_scores": vector_scores,
        "evidence": evidence,
        "raw": parsed,
    }


def reconcile_pair(score_a: int, score_b: int, threshold: int = 25) -> dict:
    """If passes differ by more than threshold, flag and keep the lower score (do not average)."""
    diff = abs(score_a - score_b)
    if diff > threshold:
        return {
            "final": min(score_a, score_b),
            "borderline_review": True,
            "disagreement": diff,
            "method": "lower_placeholder_not_averaged",
        }
    return {
        "final": (score_a + score_b) / 2.0,
        "borderline_review": False,
        "disagreement": diff,
        "method": "average",
    }


def determine_verdict(
    final_blended_score: float,
    any_borderline: bool,
    floor_violation: bool,
    exemption_pass: float = 75,
    completion_pass: float = 50,
) -> str:
    if any_borderline:
        return "BORDERLINE — HUMAN REVIEW REQUIRED"
    if final_blended_score >= exemption_pass and not floor_violation:
        return "EXEMPTED"
    if final_blended_score >= completion_pass:
        return "COMPLETION PASS — TRAINING RECOMMENDED, NOT EXEMPTED"
    return "FAIL — FULL TRAINING REQUIRED"


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def score_module(
    module_config: dict,
    vector_config: dict,
    submission: dict,
    defense_qa: list[dict[str, str]],
    rubric_config: dict | None = None,
) -> dict:
    from llm import load_rubric

    rubric_config = rubric_config or load_rubric()
    blend = rubric_config["blend"]
    cutoffs = rubric_config["cutoffs"]
    threshold = rubric_config["consistency_rule"]["disagreement_threshold"]

    pass_a = score_pass(module_config, vector_config, submission, defense_qa, "Assessor A")
    pass_b = score_pass(module_config, vector_config, submission, defense_qa, "Assessor B")

    skill_final = {}
    vector_final = {}
    flags = []

    for name in _skill_names(module_config):
        resolved = reconcile_pair(
            pass_a["skill_scores"][name],
            pass_b["skill_scores"][name],
            threshold=threshold,
        )
        skill_final[name] = resolved
        if resolved["borderline_review"]:
            flags.append({"item": name, "kind": "skill", **resolved})

    for code in mapped_vector_codes(module_config):
        resolved = reconcile_pair(
            pass_a["vector_scores"][code],
            pass_b["vector_scores"][code],
            threshold=threshold,
        )
        vector_final[code] = resolved
        if resolved["borderline_review"]:
            flags.append({"item": code, "kind": "vector", **resolved})

    module_score = _mean([item["final"] for item in skill_final.values()])

    if module_config.get("vector_blend") == "all_six" or module_config.get("id") == 9:
        weights = module_config.get("vector_blend_weights") or {}
        vector_score = sum(
            vector_final[code]["final"] * float(weights.get(code, 0.1667))
            for code in vector_final
        )
    else:
        vector_score = _mean([item["final"] for item in vector_final.values()])

    final_blended_score = (
        module_score * float(blend["module_weight"])
        + vector_score * float(blend["vector_weight"])
    )

    floor = float(cutoffs["exemption_floor_per_dimension"])
    floor_violation = any(item["final"] < floor for item in skill_final.values()) or any(
        item["final"] < floor for item in vector_final.values()
    )
    any_borderline = bool(flags)
    verdict = determine_verdict(
        final_blended_score,
        any_borderline,
        floor_violation,
        exemption_pass=float(cutoffs["exemption_pass"]),
        completion_pass=float(cutoffs["completion_pass"]),
    )

    return {
        "pass_a": pass_a,
        "pass_b": pass_b,
        "skill_final": skill_final,
        "vector_final": vector_final,
        "borderline_flags": flags,
        "borderline_review": any_borderline,
        "module_score": round(module_score, 2),
        "vector_score": round(vector_score, 2),
        "final_blended_score": round(final_blended_score, 2),
        "floor_violation": floor_violation,
        "verdict": verdict,
        "blend": blend,
        "cutoffs": cutoffs,
    }
