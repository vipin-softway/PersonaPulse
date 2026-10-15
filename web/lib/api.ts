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

/** Fetch JSON from the API with a timeout and a friendly error message. */
export async function apiFetch<T>(path: string, init: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const { timeoutMs = 15000, ...rest } = init;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...rest,
      headers: { "Content-Type": "application/json", ...rest.headers },
      signal: controller.signal,
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new ApiError(body?.detail || body?.error || `Request failed (${res.status})`, res.status);
    }
    return body as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ApiError("The server took too long to respond. Please try again.");
    }
    throw new ApiError("Can't reach the PersonaPulse API right now.");
  } finally {
    clearTimeout(timer);
  }
}
