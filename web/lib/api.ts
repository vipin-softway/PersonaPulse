import type { Backtest, NewTestInput, ProductLookup, TestResult } from "./types";

// NEXT_PUBLIC_API_URL is inlined at build time (see Dockerfile build arg).
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080").replace(/\/$/, "");

export type Health = {
  status: string;
  service: string;
  version: string;
  project_configured: boolean;
  location: string;
  max_live_personas: number;
  label: string;
};

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
  }
}

function friendlyMessage(status: number, body: { detail?: unknown; error?: unknown }): string {
  // Our API sends human-readable `detail`/`error` strings for 429 and 5xx; FastAPI defaults are not.
  const msg = typeof body?.detail === "string" ? body.detail : typeof body?.error === "string" ? body.error : "";
  if (status === 429) return msg || "You're going a bit fast. Please wait a minute and try again.";
  if (status === 404) return msg && msg !== "Not Found" ? msg : "We couldn't find that test. Please refresh the page.";
  if (status === 422) return "Some of the details look invalid. Please check the form and try again.";
  if (status >= 500) return msg || "Something went wrong on our side. Please try again in a moment.";
  return msg && msg !== "Not Found" ? msg : `Request failed (${status}).`;
}

/** Fetch JSON from the API with a timeout and a friendly error message. */
export async function apiFetch<T>(path: string, init: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const { timeoutMs = 15000, signal, ...rest } = init;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  signal?.addEventListener("abort", () => controller.abort(signal.reason)); // caller cancelled
  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...rest,
      headers: { "Content-Type": "application/json", ...rest.headers },
      signal: controller.signal,
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(friendlyMessage(res.status, body), res.status);
    return body as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (signal?.aborted) throw signal.reason ?? e;
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ApiError("The server took too long to respond. Please try again.");
    }
    throw new ApiError("Can't reach the PersonaPulse API right now.");
  } finally {
    clearTimeout(timer);
  }
}

// --- Endpoints ---------------------------------------------------------------

// Live simulations call Gemini for ~30 personas, so allow well over a minute.
const LIVE_TIMEOUT_MS = 150_000;

export const getTest = (id: string) =>
  id === "demo" ? apiFetch<TestResult>("/demo", { timeoutMs: 20000 }) : apiFetch<TestResult>(`/tests/${encodeURIComponent(id)}`, { timeoutMs: 20000 });

export const createTest = (input: NewTestInput, signal?: AbortSignal) =>
  apiFetch<TestResult>("/tests", { method: "POST", body: JSON.stringify(input), timeoutMs: LIVE_TIMEOUT_MS, signal });

export const improveTest = (id: string, variantId: string) =>
  apiFetch<TestResult>(`/tests/${encodeURIComponent(id)}/improve`, {
    method: "POST",
    body: JSON.stringify({ variant_id: variantId }),
    timeoutMs: LIVE_TIMEOUT_MS,
  });

export const suggestImprovements = (id: string, constraints?: string) =>
  apiFetch<TestResult>(`/tests/${encodeURIComponent(id)}/improve`, {
    method: "POST",
    body: JSON.stringify({ constraints: constraints?.trim() || undefined }),
    timeoutMs: LIVE_TIMEOUT_MS,
  });

// One Gemini call with Google Search grounding, usually 5-15 s.
export const lookupProduct = (query: string) =>
  apiFetch<ProductLookup>("/lookup", { method: "POST", body: JSON.stringify({ query }), timeoutMs: 60_000 });

export const getBacktest = () => apiFetch<Backtest>("/backtest", { timeoutMs: 20000 });
