import { loadVector, mappedVectorCodes } from "./config";
import { chat, extractJson } from "./llm";
import type { ModuleConfig, Submission } from "./types";

export async function generateDefenseQuestions(
  moduleConfig: ModuleConfig,
  submission: Submission,
): Promise<string[]> {
  const vectorConfig = loadVector();
  const vectorDims = mappedVectorCodes(moduleConfig);
  const skills = (moduleConfig.skill_indices || []).map(
    (idx) => `- ${idx.name}: ${idx.observable_behaviour}`,
  );
  const dimBlocks = vectorDims.map((code) => {
    const dim = vectorConfig.dimensions[code];
    return `- ${code} ${dim.name}: ${dim.definition}`;
  });
  const written = submission.text || submission.written || "";
  const code = submission.code || "";
  const user = `You are preparing a short oral-defense substitute (written questions).

MODULE: ${moduleConfig.id} ${moduleConfig.name}

SKILL INDICES
${skills.join("\n")}

RELEVANT VECTOR DIMENSIONS
${dimBlocks.join("\n")}

SUBMISSION (written)
${written}

SUBMISSION (code)
${code}

Instructions:
- Identify the 1-2 weakest-evidenced skill indices or VECTOR dimensions in THIS specific submission.
- Write 2-3 pointed follow-up questions that would only be answerable if the candidate actually understands that weak spot.
- Questions must reference specifics from the submission (names, choices, missing artefacts, vague claims). Not generic.
- Do not score yet.

Return STRICT JSON only:
{"weak_spots": ["..."], "questions": ["question 1", "question 2", "question 3"]}
`;
  const raw = await chat(
    [
      {
        role: "system",
        content:
          "You write sharp, evidence-based defense questions. Return JSON only. Reference the submission; never invent artefacts the candidate did not mention.",
      },
      { role: "user", content: user },
    ],
    { temperature: 0.4, jsonObject: true, maxTokens: 1500 },
  );
  const parsed = extractJson(raw);
  const questions = Array.isArray(parsed.questions) ? parsed.questions : [];
  const cleaned = questions.map((q) => String(q).trim()).filter(Boolean);
  if (cleaned.length < 2) {
    throw new Error("Defense step did not return at least 2 questions. Please retry.");
  }
  return cleaned.slice(0, 3);
}
