import { GROK_MODEL } from "./constants";
import { getModule } from "./config";
import { chat } from "./llm";
import type { ModuleConfig } from "./types";

const SLOT_INSTRUCTIONS = `You are writing a Manning liveProject-style capstone brief for an FDE trainee.

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

Do not add extra sections. Do not ask questions back. Output only the problem statement.`;

export function buildCapstonePrompt(
  module: ModuleConfig,
  domain: string,
  tools: string[],
  hyperscaler: string | null,
): string {
  const skills = (module.skill_indices || []).map(
    (idx) => `- ${idx.name}: ${idx.observable_behaviour}`,
  );
  const toolsText = tools.length ? tools.join(", ") : "none specified";
  const cloudText = hyperscaler || "None (no hyperscaler required)";
  return `${SLOT_INSTRUCTIONS}

MODULE
- id: ${module.id}
- name: ${module.name}
- phase_ref: ${module.phase_ref}

SKILL INDICES (every one must be exercisable by the deliverable spec)
${skills.join("\n")}

CANDIDATE CHOICES
- domain: ${domain}
- AI tools used: ${toolsText}
- hyperscaler: ${cloudText}
`;
}

export async function generateCapstoneBundle(
  moduleId: number,
  domain: string,
  tools: string[],
  hyperscaler: string | null,
) {
  const module = getModule(moduleId);
  const prompt = buildCapstonePrompt(module, domain, tools, hyperscaler);
  const statement = await chat(
    [
      {
        role: "system",
        content:
          "You write Manning liveProject briefs. Follow the user's slot template exactly. Do not freelance extra sections.",
      },
      { role: "user", content: prompt },
    ],
    { temperature: 0.7, maxTokens: 2500 },
  );
  return {
    problem_statement: statement.trim(),
    prompt,
    model: GROK_MODEL,
    module,
  };
}
