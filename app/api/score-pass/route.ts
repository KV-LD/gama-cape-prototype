import { NextResponse } from "next/server";
import { getModule, loadVector } from "@/lib/config";
import { jsonError, readError } from "@/lib/http";
import { scorePass } from "@/lib/scorer";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      module_id?: number;
      submission?: { written?: string; code?: string; text?: string };
      defense_qa?: { question: string; answer: string }[];
      pass_label?: string;
    };
    if (!body.module_id || !body.submission || !body.defense_qa || !body.pass_label) {
      return jsonError("module_id, submission, defense_qa, and pass_label are required.");
    }
    const written = (body.submission.written || "").trim();
    const code = (body.submission.code || "").trim();
    const submission = {
      written,
      code,
      text: body.submission.text || (written + "\n\n--- CODE ---\n\n" + code).trim(),
    };
    const result = await scorePass(
      getModule(Number(body.module_id)),
      loadVector(),
      submission,
      body.defense_qa,
      body.pass_label,
    );
    return NextResponse.json(result);
  } catch (error) {
    return jsonError(readError(error), 500);
  }
}
