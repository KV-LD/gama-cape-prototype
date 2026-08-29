import { NextResponse } from "next/server";
import { getModule } from "@/lib/config";
import { generateDefenseQuestions } from "@/lib/defense";
import { jsonError, readError } from "@/lib/http";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      module_id?: number;
      submission?: { written?: string; code?: string; text?: string };
    };
    if (!body.module_id || !body.submission) {
      return jsonError("module_id and submission are required.");
    }
    const written = (body.submission.written || "").trim();
    const code = (body.submission.code || "").trim();
    if (!written) return jsonError("Written notes are required.");
    const submission = {
      written,
      code,
      text: (written + "\n\n--- CODE ---\n\n" + code).trim(),
    };
    const questions = await generateDefenseQuestions(getModule(Number(body.module_id)), submission);
    return NextResponse.json({ questions });
  } catch (error) {
    return jsonError(readError(error), 500);
  }
}
