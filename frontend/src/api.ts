import type { AskOptions, AskResponse, Config, EvalReport, Health } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      const d = body?.detail;
      if (Array.isArray(d)) detail = d.map((x: { msg?: string }) => x.msg ?? "invalid input").join("; ");
      else if (d) detail = String(d);
    } catch { /* not JSON */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),
  config: () => request<Config>("/api/config"),
  ask: (question: string, opts: AskOptions = {}) =>
    request<AskResponse>("/api/ask", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ question, ...opts }),
    }),
  evalResults: () => request<EvalReport>("/api/eval/results"),
};
