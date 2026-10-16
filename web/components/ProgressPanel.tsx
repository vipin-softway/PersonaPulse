"use client";

import { useEffect, useState } from "react";

const STEPS = [
  { at: 0, label: "Briefing the AI customers on your product" },
  { at: 4, label: "Each customer is reacting independently" },
  { at: 35, label: "Summarising objections and insights" },
  { at: 55, label: "Almost there, a few customers are still deciding" },
];

/** Time-based progress for a 20–60 s simulation. It's an estimate; the request finishes when it finishes. */
export default function ProgressPanel({ personas, title = "Running your test", onCancel }: { personas: number; title?: string; onCancel?: () => void }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const id = setInterval(() => setElapsed((Date.now() - start) / 1000), 250);
    return () => clearInterval(id);
  }, []);

  // Eases towards 95% over ~60 s and never claims to be finished.
  const pct = Math.min(95, 100 * (1 - Math.exp(-elapsed / 25)));
  const current = STEPS.filter((s) => elapsed >= s.at).length - 1;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm" role="status" aria-live="polite">
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-lg font-semibold">{title}</h2>
        <span className="text-sm text-slate-500 tabular-nums">{Math.floor(elapsed)}s</span>
      </div>
      <p className="mt-1 text-sm text-slate-500">
        {personas} AI customers are evaluating it. This usually takes 20–60 seconds; please keep this tab open.
      </p>

      <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-indigo-600 transition-[width] duration-300" style={{ width: `${pct}%` }} />
      </div>

      <ol className="mt-5 space-y-2 text-sm">
        {STEPS.map((s, i) => (
          <li key={s.label} className={`flex items-center gap-2 ${i <= current ? "text-slate-900" : "text-slate-400"}`}>
            <span
              className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] ${
                i < current ? "bg-emerald-500 text-white" : i === current ? "bg-indigo-600 text-white" : "bg-slate-100"
              }`}
              aria-hidden
            >
              {i < current ? "✓" : i + 1}
            </span>
            {s.label}
          </li>
        ))}
      </ol>
      {onCancel && (
        <button type="button" onClick={onCancel} className="mt-5 text-sm font-medium text-slate-500 underline hover:text-slate-800">
          Cancel and edit the product
        </button>
      )}
    </div>
  );
}
