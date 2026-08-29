export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const raw = await resp.text();
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error(
      `Empty reply from ${url} (HTTP ${resp.status}). Wait a few seconds and try again.`,
    );
  }
  if (trimmed.startsWith("<") || trimmed.toLowerCase().startsWith("<!doctype")) {
    throw new Error(
      "The AI step took too long and Netlify sent a web page instead of an answer (this is a timeout, not a problem with your text). Wait 15 seconds and click the same button again. Keep written notes under 250 words and each defense answer under 70 words. If it keeps failing, open JSON → HTML and upload an existing record.json to finish a demo of the report.",
    );
  }
  let data: T & { error?: string };
  try {
    data = JSON.parse(trimmed) as T & { error?: string };
  } catch {
    throw new Error(
      `The server did not return JSON (HTTP ${resp.status}): ${trimmed.slice(0, 180)}`,
    );
  }
  if (!resp.ok) throw new Error(data.error || `Request failed (HTTP ${resp.status})`);
  return data;
}
