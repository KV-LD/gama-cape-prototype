"""Defense step: 2-3 written challenge questions on the weakest evidence."""

from __future__ import annotations

from typing import Any

from llm import chat, extract_json, mapped_vector_codes


def generate_defense_questions(
    module_config: dict,
    vector_dims: list[str],
    submission: dict,
    vector_config: dict | None = None,
) -> list[str]:
    from llm import load_vector

    vector_config = vector_config or load_vector()
    skills = []
    for idx in module_config.get("skill_indices") or []:
        skills.append(f"- {idx['name']}: {idx['observable_behaviour']}")

    dim_blocks = []
    for code in vector_dims:
        dim = vector_config["dimensions"][code]
        dim_blocks.append(f"- {code} {dim['name']}: {dim['definition']}")

    written = submission.get("text") or submission.get("written") or ""
    code = submission.get("code") or ""
    user = f"""You are preparing a short oral-defense substitute (written questions).

MODULE: {module_config['id']} {module_config['name']}

SKILL INDICES
{chr(10).join(skills)}

RELEVANT VECTOR DIMENSIONS
{chr(10).join(dim_blocks)}

SUBMISSION (written)
{written}

SUBMISSION (code)
{code}

Instructions:
- Identify the 1-2 weakest-evidenced skill indices or VECTOR dimensions in THIS specific submission.
- Write 2-3 pointed follow-up questions that would only be answerable if the candidate actually understands that weak spot.
- Questions must reference specifics from the submission (names, choices, missing artefacts, vague claims). Not generic.
- Do not score yet.

Return STRICT JSON only:
{{"weak_spots": ["..."], "questions": ["question 1", "question 2", "question 3"]}}
"""
    raw = chat(
        [
            {
                "role": "system",
                "content": (
                    "You write sharp, evidence-based defense questions. "
                    "Return JSON only. Reference the submission; never invent artefacts the candidate did not mention."
                ),
            },
            {"role": "user", "content": user},
        ],
        temperature=0.4,
        json_object=True,
        max_tokens=1500,
    )
    parsed = extract_json(raw)
    questions = parsed.get("questions") or []
    cleaned = [str(q).strip() for q in questions if str(q).strip()]
    if len(cleaned) < 2:
        raise RuntimeError("Defense step did not return at least 2 questions. Please rerun.")
    return cleaned[:3]


def conduct_defense(
    module_config: dict,
    submission: dict,
    vector_config: dict | None = None,
    answers: list[str] | None = None,
) -> list[dict[str, str]]:
    vector_dims = mapped_vector_codes(module_config)
    questions = generate_defense_questions(
        module_config, vector_dims, submission, vector_config=vector_config
    )
    pairs: list[dict[str, str]] = []
    print()
    print("=" * 72)
    print("DEFENSE QUESTIONS")
    print("These target the weakest parts of what you submitted.")
    print("=" * 72)
    for i, question in enumerate(questions, start=1):
        print()
        print(f"Question {i} of {len(questions)}:")
        print(question)
        if answers is not None:
            answer = answers[i - 1] if i - 1 < len(answers) else ""
            print(f"(recorded answer) {answer}")
        else:
            answer = input("Your answer: ").strip()
        pairs.append({"question": question, "answer": answer})
    return pairs
