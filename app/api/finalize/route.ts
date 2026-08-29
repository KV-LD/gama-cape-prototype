import { NextResponse } from "next/server";
import { getModule, mappedVectorCodes } from "@/lib/config";
import { jsonError, readError } from "@/lib/http";
import { renderReport } from "@/lib/report";
import { reconcileScores } from "@/lib/scorer";
import { commitAttempt } from "@/lib/store";
import type { AttemptRecord, ScorePass, Submission } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      candidate_name?: string;
      domain?: string;
      module_id?: number;
      tools?: string[];
      hyperscaler?: string | null;
      problem_statement?: string;
      generation_prompt?: string;
      generation_model?: string;
      submission?: Submission;
      defense_qa?: { question: string; answer: string }[];
      pass_a?: ScorePass;
      pass_b?: ScorePass;
    };
    if (
      !body.candidate_name ||
      !body.domain ||
      !body.module_id ||
      !body.tools?.length ||
      !body.problem_statement ||
      !body.submission ||
      !body.defense_qa ||
      !body.pass_a ||
      !body.pass_b
    ) {
      return jsonError("Missing fields required to finalize the attempt.");
    }
    const module = getModule(Number(body.module_id));
    const written = (body.submission.written || "").trim();
    const code = (body.submission.code || "").trim();
    const submission: Submission = {
      written,
      code,
      text: body.submission.text || (written + "\n\n--- CODE ---\n\n" + code).trim(),
    };
    const scoreSheet = reconcileScores(module, body.pass_a, body.pass_b);
    const record: AttemptRecord = {
      candidate_name: body.candidate_name,
      domain: body.domain,
      module_id: module.id,
      module_name: module.name,
      tools: body.tools,
      hyperscaler: body.hyperscaler && body.hyperscaler !== "None" ? body.hyperscaler : null,
      problem_statement: body.problem_statement,
      generation_prompt: body.generation_prompt || "",
      generation_model: body.generation_model,
      submission,
      defense_qa: body.defense_qa,
      score_sheet: scoreSheet,
      pass_a: scoreSheet.pass_a,
      pass_b: scoreSheet.pass_b,
      verdict: scoreSheet.verdict,
      mapped_vector_dimensions: mappedVectorCodes(module),
    };
    const urls = await commitAttempt(record);
    record.github_url = urls.github_url;
    record.html_report_url = urls.html_report_url;
    return NextResponse.json({
      record,
      html: renderReport(record),
    });
  } catch (error) {
    return jsonError(readError(error), 500);
  }
}
