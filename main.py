#!/usr/bin/env python3
"""GAMA CAPE CLI — intake → capstone → defense → score → GitHub audit record."""

from __future__ import annotations

from defense import conduct_defense
from intake import run_intake
from llm import load_vector, mapped_vector_codes
from scorer import score_module
from store import commit_attempt


def print_score_sheet(score_sheet: dict, github_url: str, module_config: dict, vector_config: dict) -> None:
    print()
    print("=" * 72)
    print("RUBRIC SCORING SHEET")
    print("=" * 72)
    print(f"Module: {module_config['id']}  {module_config['name']}")
    print()
    print("Skill indices")
    print("-" * 72)
    for name, item in score_sheet["skill_final"].items():
        flag = "  << HUMAN REVIEW" if item["borderline_review"] else ""
        print(f"  {name:40s}  {item['final']:>6.1f}{flag}")
    print()
    print("VECTOR dimensions")
    print("-" * 72)
    for code, item in score_sheet["vector_final"].items():
        dim_name = vector_config["dimensions"][code]["name"]
        flag = "  << HUMAN REVIEW" if item["borderline_review"] else ""
        print(f"  {code} {dim_name:36s}  {item['final']:>6.1f}{flag}")
    print()
    print("-" * 72)
    print(f"  Module score (mean of skills)     {score_sheet['module_score']:.2f}")
    print(f"  VECTOR score                      {score_sheet['vector_score']:.2f}")
    print(f"  Blended (60% module / 40% VECTOR) {score_sheet['final_blended_score']:.2f}")
    print()
    print(f"VERDICT: {score_sheet['verdict']}")
    print()
    print(f"Audit record on GitHub:")
    print(f"  {github_url}")
    print("=" * 72)


def build_record(intake: dict, defense_qa: list, score_sheet: dict, github_url: str) -> dict:
    return {
        "candidate_name": intake["candidate_name"],
        "domain": intake["domain"],
        "module_id": intake["module_id"],
        "module_name": intake["module_name"],
        "tools": intake["tools"],
        "hyperscaler": intake["hyperscaler"],
        "problem_statement": intake["problem_statement"],
        "generation_prompt": intake["generation_prompt"],
        "generation_model": intake.get("generation_model"),
        "submission": intake["submission"],
        "defense_qa": defense_qa,
        "score_sheet": score_sheet,
        "pass_a": score_sheet["pass_a"],
        "pass_b": score_sheet["pass_b"],
        "verdict": score_sheet["verdict"],
        "github_url": github_url,
        "mapped_vector_dimensions": mapped_vector_codes(intake["module_config"]),
    }


def run_pipeline(intake: dict | None = None, defense_answers: list[str] | None = None) -> dict:
    vector_config = load_vector()
    if intake is None:
        intake = run_intake()
    defense_qa = conduct_defense(
        intake["module_config"],
        intake["submission"],
        vector_config=vector_config,
        answers=defense_answers,
    )
    print()
    print("Scoring with two independent assessor passes. This can take a minute...")
    score_sheet = score_module(
        intake["module_config"],
        vector_config,
        intake["submission"],
        defense_qa,
    )
    record_without_url = build_record(intake, defense_qa, score_sheet, github_url="")
    github_url = commit_attempt(record_without_url)
    record = build_record(intake, defense_qa, score_sheet, github_url)
    print_score_sheet(score_sheet, github_url, intake["module_config"], vector_config)
    return record


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
