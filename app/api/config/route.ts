import { NextResponse } from "next/server";
import { AI_TOOLS, DOMAINS, HYPERSCALERS } from "@/lib/constants";
import { loadRubric } from "@/lib/config";

export const runtime = "nodejs";

export async function GET() {
  const rubric = loadRubric();
  return NextResponse.json({
    domains: DOMAINS,
    tools: AI_TOOLS,
    hyperscalers: HYPERSCALERS,
    modules: rubric.modules.map((module) => ({
      id: module.id,
      name: module.name,
      exemptible: module.exemptible !== false,
      phase_ref: module.phase_ref,
      skill_indices: module.skill_indices,
    })),
  });
}
