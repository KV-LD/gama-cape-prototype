export const DOMAINS = [
  "healthcare",
  "retail",
  "bfsi",
  "manufacturing",
  "supply chain",
  "automotive",
] as const;

export const AI_TOOLS = ["Claude", "Copilot", "Gemini", "Cursor", "Devin"] as const;

export const HYPERSCALERS = ["AWS", "Azure", "GCP", "None"] as const;

export const GROK_MODEL = "x-ai/grok-4.5";
export const OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions";
export const ALLOWED_SCORES = [0, 25, 50, 75, 100] as const;
export const DEFAULT_REPO = "KV-LD/gama-cape-prototype";
