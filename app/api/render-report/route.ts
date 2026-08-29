import { NextResponse } from "next/server";
import { jsonError, readError } from "@/lib/http";
import { renderReport } from "@/lib/report";
import type { AttemptRecord } from "@/lib/types";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const record = (await request.json()) as AttemptRecord;
    if (!record || typeof record !== "object") {
      return jsonError("Paste a CAPE record.json object.");
    }
    const html = renderReport(record);
    return NextResponse.json({ html });
  } catch (error) {
    return jsonError(readError(error), 400);
  }
}
