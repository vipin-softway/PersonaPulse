"use client";

import { useEffect, useState } from "react";
import { apiFetch, type Health } from "@/lib/api";

type State = { kind: "loading" } | { kind: "ok"; health: Health } | { kind: "error"; message: string };

export default function HealthStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    // Cloud Run may cold-start (min instances 0), so allow a generous timeout.
    apiFetch<Health>("/health", { timeoutMs: 20000 })
      .then((health) => setState({ kind: "ok", health }))
      .catch((e: Error) => setState({ kind: "error", message: e.message }));
  }, []);

  const dot =
    state.kind === "ok" ? "bg-emerald-500" : state.kind === "error" ? "bg-amber-500" : "bg-slate-400 animate-pulse";
  const text =
    state.kind === "ok"
      ? `API online · v${state.health.version} · up to ${state.health.max_live_personas} live personas`
      : state.kind === "error"
        ? state.message
        : "Waking up the API…";

  return (
    <p className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600">
      <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden />
      {text}
    </p>
  );
}
