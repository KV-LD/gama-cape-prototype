import { ALLOWED_SCORES, GROK_MODEL, OPENROUTER_CHAT_URL } from "./constants";

function readSecret(name: string): string {
  // Bracket access so Next.js does not freeze an empty value at build time.
  let value = (process.env[name] || "").trim();
  if (
    (value.startsWith("\"") && value.endsWith("\"")) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1).trim();
  }
  if (value.toLowerCase().startsWith("bearer ")) {
    value = value.slice(7).trim();
  }
  return value;
}

export function openrouterKey(): string {
  const key = readSecret("OPENROUTER_API_KEY");
  if (!key || key === "your_key_here") {
    throw new Error(
      "OPENROUTER_API_KEY is missing. In Netlify go to Site configuration → Environment variables, add OPENROUTER_API_KEY, then Trigger deploy.",
    );
  }
  return key;
}

export function githubToken(): string {
  const token = readSecret("GITHUB_TOKEN");
  if (!token || token === "your_token_here") {
    throw new Error(
      "GITHUB_TOKEN is missing. In Netlify go to Site configuration → Environment variables, add GITHUB_TOKEN, then Trigger deploy.",
    );
  }
  return token;
}

export async function chat(
  messages: { role: string; content: string }[],
  options?: { temperature?: number; jsonObject?: boolean; maxTokens?: number },
): Promise<string> {
  let maxTokens = options?.maxTokens ?? 2000;
  let lastDetails = "";

  for (let attempt = 0; attempt < 2; attempt++) {
    const body: Record<string, unknown> = {
      model: GROK_MODEL,
      messages,
      temperature: options?.temperature ?? 0.4,
      max_tokens: maxTokens,
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

    if (resp.ok) {
      const data = (await resp.json()) as {
        choices?: { message?: { content?: string } }[];
      };
      const content = data.choices?.[0]?.message?.content;
      if (typeof content !== "string") {
        throw new Error(`Unexpected OpenRouter response: ${JSON.stringify(data).slice(0, 400)}`);
      }
      return content;
    }

    lastDetails = (await resp.text()).slice(0, 500);
    if (resp.status === 402 && attempt === 0) {
      const afforded = lastDetails.match(/can only afford (\d+)/i);
      const cheaper = afforded ? Math.max(256, Number(afforded[1]) - 50) : Math.min(1500, maxTokens);
      if (cheaper < maxTokens) {
        maxTokens = cheaper;
        continue;
      }
    }
    throw new Error(`OpenRouter chat failed (HTTP ${resp.status}). Details: ${lastDetails}`);
  }

  throw new Error(`OpenRouter chat failed. Details: ${lastDetails}`);
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
