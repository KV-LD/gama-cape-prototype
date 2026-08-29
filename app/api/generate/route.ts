import { NextResponse } from "next/server";
import { generateCapstoneBundle } from "@/lib/generate";
import { jsonError, readError } from "@/lib/http";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      module_id?: number;
      domain?: string;
      tools?: string[];
      hyperscaler?: string | null;
    };
    if (!body.module_id || !body.domain || !body.tools?.length) {
      return jsonError("module_id, domain, and at least one tool are required.");
    }
    const hyperscaler = body.hyperscaler && body.hyperscaler !== "None" ? body.hyperscaler : null;
    const bundle = await generateCapstoneBundle(
      Number(body.module_id),
      body.domain,
      body.tools,
      hyperscaler,
    );
    return NextResponse.json({
      problem_statement: bundle.problem_statement,
      generation_prompt: bundle.prompt,
      generation_model: bundle.model,
      module: {
        id: bundle.module.id,
        name: bundle.module.name,
      },
    });
  } catch (error) {
    return jsonError(readError(error), 500);
  }
}
