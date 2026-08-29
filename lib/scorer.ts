import { loadRubric, mappedVectorCodes } from "./config";
import { chat, clampScore, extractJson } from "./llm";
import type {
  DefenseQA,
  ModuleConfig,
  Reconciled,
  ScorePass,
  ScoreSheet,
  Submission,
  VectorConfig,
} from "./types";

function skillNames(moduleConfig: ModuleConfig): string[] {
  return (moduleConfig.skill_indices || []).map((s) => s.name);
}

export async function scorePass(
  moduleConfig: ModuleConfig,
  vectorConfig: VectorConfig,
  submission: Submission,
  defenseQa: DefenseQA[],
  passLabel: string,
): Promise<ScorePass> {
  const names = skillNames(moduleConfig);
  const vectorCodes = mappedVectorCodes(moduleConfig);
  const skillLines = (moduleConfig.skill_indices || []).map(
    (idx) => `- ${idx.name}: ${idx.observable_behaviour}`,
  );
  const mapping = vectorConfig.score_band_mapping;
  const vecLines: string[] = [];
  for (const code of vectorCodes) {
    const dim = vectorConfig.dimensions[code];
    vecLines.push(`${code} ${dim.name}: ${dim.definition}`);
    vecLines.push(`  1 Emerging -> ${mapping["1_Emerging"]}: ${dim.levels["1"]}`);
    vecLines.push(`  2 Developing -> ${mapping["2_Developing"]}: ${dim.levels["2"]}`);
    vecLines.push(`  3 Established -> ${mapping["3_Established"]}: ${dim.levels["3"]}`);
    vecLines.push(`  4 Advanced -> ${mapping["4_Advanced"]}: ${dim.levels["4"]}`);
    vecLines.push(`  5 Defining -> ${mapping["5_Defining"]}: ${dim.levels["5"]}`);
  }
  const qaLines = defenseQa.flatMap((pair) => [
    `Q: ${pair.question || ""}`,
    `A: ${pair.answer || ""}`,
  ]);
  const written = submission.text || submission.written || "";
  const code = submission.code || "";
  const user = `You are ${passLabel}, an independent assessor. Do not coordinate with any other assessor.
Score ONLY from evidence in the submission and defense answers. If a skill index is not evidenced, score 0.
Do NOT invent praise. Do NOT infer competence that is not shown.

Allowed numeric scores only: 0, 25, 50, 75, 100.
FDE scale: Not Evidenced=0, Below Expectations=25, Meets Expectations=50, Above Average Can Improve=75, Complete & Clear=100.
VECTOR levels map 1:1 onto that same number line.

MODULE: ${moduleConfig.id} ${moduleConfig.name}

SKILL INDICES TO SCORE (every one)
${skillLines.join("\n")}

VECTOR DIMENSIONS TO SCORE (every one listed)
${vecLines.join("\n")}

SUBMISSION (written)
${written}

SUBMISSION (code)
${code}

DEFENSE Q&A
${qaLines.join("\n")}

Return STRICT JSON only with this shape:
{
  "skill_scores": { ${names.map((n) => `"${n}": <0|25|50|75|100>`).join(", ")} },
  "vector_scores": { ${vectorCodes.map((c) => `"${c}": <0|25|50|75|100>`).join(", ")} },
  "evidence": {
    "<skill or vector code>": "cite the specific sentence/artefact (or state ABSENT)"
  }
}
`;
  const raw = await chat(
    [
      {
        role: "system",
        content: `You are ${passLabel}. Independent evidence-based assessor. JSON only. Score 0 when evidence is absent. Never invent work product.`,
      },
      { role: "user", content: user },
    ],
    { temperature: 0.35, jsonObject: true, maxTokens: 2000 },
  );
  const parsed = extractJson(raw);
  const skillScores: Record<string, number> = {};
  const parsedSkills = (parsed.skill_scores || {}) as Record<string, unknown>;
  for (const name of names) skillScores[name] = clampScore(parsedSkills[name] ?? 0);
  const vectorScores: Record<string, number> = {};
  const parsedVectors = (parsed.vector_scores || {}) as Record<string, unknown>;
  for (const code of vectorCodes) vectorScores[code] = clampScore(parsedVectors[code] ?? 0);
  const evidence = (parsed.evidence || {}) as Record<string, string>;
  return {
    pass_label: passLabel,
    skill_scores: skillScores,
    vector_scores: vectorScores,
    evidence,
    raw: parsed,
  };
}

export function reconcilePair(scoreA: number, scoreB: number, threshold = 25): Reconciled {
  const diff = Math.abs(scoreA - scoreB);
  if (diff > threshold) {
    return {
      final: Math.min(scoreA, scoreB),
      borderline_review: true,
      disagreement: diff,
      method: "lower_placeholder_not_averaged",
    };
  }
  return {
    final: (scoreA + scoreB) / 2,
    borderline_review: false,
    disagreement: diff,
    method: "average",
  };
}

export function determineVerdict(
  finalBlendedScore: number,
  anyBorderline: boolean,
  floorViolation: boolean,
  exemptionPass = 75,
  completionPass = 50,
): string {
  if (anyBorderline) return "BORDERLINE — HUMAN REVIEW REQUIRED";
  if (finalBlendedScore >= exemptionPass && !floorViolation) return "EXEMPTED";
  if (finalBlendedScore >= completionPass) {
    return "COMPLETION PASS — TRAINING RECOMMENDED, NOT EXEMPTED";
  }
  return "FAIL — FULL TRAINING REQUIRED";
}

function mean(values: number[]): number {
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

export function reconcileScores(
  moduleConfig: ModuleConfig,
  passA: ScorePass,
  passB: ScorePass,
): ScoreSheet {
  const rubric = loadRubric();
  const blend = rubric.blend;
  const cutoffs = rubric.cutoffs;
  const threshold = rubric.consistency_rule.disagreement_threshold;
  const skillFinal: Record<string, Reconciled> = {};
  const vectorFinal: Record<string, Reconciled> = {};
  const flags: unknown[] = [];

  for (const name of skillNames(moduleConfig)) {
    const resolved = reconcilePair(
      passA.skill_scores[name],
      passB.skill_scores[name],
      threshold,
    );
    skillFinal[name] = resolved;
    if (resolved.borderline_review) flags.push({ item: name, kind: "skill", ...resolved });
  }
  for (const code of mappedVectorCodes(moduleConfig)) {
    const resolved = reconcilePair(
      passA.vector_scores[code],
      passB.vector_scores[code],
      threshold,
    );
    vectorFinal[code] = resolved;
    if (resolved.borderline_review) flags.push({ item: code, kind: "vector", ...resolved });
  }

  const moduleScore = mean(Object.values(skillFinal).map((item) => item.final));
  let vectorScore: number;
  if (moduleConfig.vector_blend === "all_six" || moduleConfig.id === 9) {
    const weights = moduleConfig.vector_blend_weights || {};
    vectorScore = Object.entries(vectorFinal).reduce(
      (sum, [code, item]) => sum + item.final * Number(weights[code] ?? 0.1667),
      0,
    );
  } else {
    vectorScore = mean(Object.values(vectorFinal).map((item) => item.final));
  }

  const finalBlendedScore =
    moduleScore * Number(blend.module_weight) + vectorScore * Number(blend.vector_weight);
  const floor = Number(cutoffs.exemption_floor_per_dimension);
  const floorViolation =
    Object.values(skillFinal).some((item) => item.final < floor) ||
    Object.values(vectorFinal).some((item) => item.final < floor);
  const anyBorderline = flags.length > 0;
  const verdict = determineVerdict(
    finalBlendedScore,
    anyBorderline,
    floorViolation,
    Number(cutoffs.exemption_pass),
    Number(cutoffs.completion_pass),
  );

  return {
    pass_a: passA,
    pass_b: passB,
    skill_final: skillFinal,
    vector_final: vectorFinal,
    borderline_flags: flags,
    borderline_review: anyBorderline,
    module_score: Math.round(moduleScore * 100) / 100,
    vector_score: Math.round(vectorScore * 100) / 100,
    final_blended_score: Math.round(finalBlendedScore * 100) / 100,
    floor_violation: floorViolation,
    verdict,
    blend,
    cutoffs,
  };
}
