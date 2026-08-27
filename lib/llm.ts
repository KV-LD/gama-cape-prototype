import { ALLOWED_SCORES, GROK_MODEL, OPENROUTER_CHAT_URL } from "./constants";

export function openrouterKey(): string {
  const key = (process.env.OPENROUTER_API_KEY || "").trim();
  if (!key) {
    throw new Error("OPENROUTER_API_KEY is missing. Add it in Vercel project environment variables.");
  }
  return key;
}

export function githubToken(): string {
  const token = (process.env.GITHUB_TOKEN || "").trim();
  if (!token) {
    throw new Error("GITHUB_TOKEN is missing. Add it in Vercel project environment variables.");
  }
  return token;
}

export async function chat(
  messages: { role: string; content: string }[],
  options?: { temperature?: number; jsonObject?: boolean; maxTokens?: number },
): Promise<string> {
  const body: Record<string, unknown> = {
    model: GROK_MODEL,
    messages,
    temperature: options?.temperature ?? 0.4,
    max_tokens: options?.maxTokens ?? 4000,
  };
  if (options?.jsonObject) {
    body.response_format = { type: "json_object" };
  }

  const resp = await fetch(OPENROUTER_CHAT_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${openrouterKey()}`,
      "Content-Type": "application/json",
      "User-Agent": "gama-cape-prototype",
      "HTTP-Referer": "https://github.com/KV-LD/gama-cape-prototype",
      "X-Title": "GAMA CAPE",
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const details = (await resp.text()).slice(0, 400);
    throw new Error(`OpenRouter chat failed (HTTP ${resp.status}). Details: ${details}`);
  }
  const data = (await resp.json()) as {
    choices?: { message?: { content?: string } }[];
  };
  const content = data.choices?.[0]?.message?.content;
  if (typeof content !== "string") {
    throw new Error(`Unexpected OpenRouter response: ${JSON.stringify(data).slice(0, 400)}`);
  }
  return content;
}

export function extractJson(text: string): Record<string, unknown> {
  const stripped = (text || "").trim();
  if (!stripped) throw new Error("Empty model reply; cannot parse JSON.");
  try {
    return JSON.parse(stripped) as Record<string, unknown>;
  } catch {
    // continue
  }
  const fence = stripped.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fence) return JSON.parse(fence[1].trim()) as Record<string, unknown>;
  const start = stripped.indexOf("{");
  const end = stripped.lastIndexOf("}");
  if (start !== -1 && end !== -1 && end > start) {
    return JSON.parse(stripped.slice(start, end + 1)) as Record<string, unknown>;
  }
  throw new Error(`Could not find JSON in model reply: ${stripped.slice(0, 240)}`);
}

export function clampScore(value: unknown): number {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  const nearest = ALLOWED_SCORES.reduce((best, score) =>
    Math.abs(score - number) < Math.abs(best - number) ? score : best,
  );
  return nearest;
}
