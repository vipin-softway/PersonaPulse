"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getTest } from "@/lib/api";
import type { TestResult } from "@/lib/types";
import { inr } from "./ui";

/** A miniature of the real demo result, so the hero shows the product rather than describing it. */
export default function HeroPreview() {
  const [test, setTest] = useState<TestResult | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getTest("demo").then(setTest).catch(() => setFailed(true));
  }, []);

  if (failed) return null;
  if (!test) return <div className="h-[420px] animate-pulse rounded-2xl bg-white/10" aria-hidden />;

  const a = test.variants[0];
  const b = test.variants[1];
  const yes = Math.round((a.overall.would_buy_pct / 100) * a.n_personas);
  const maybe = Math.round((a.overall.maybe_pct / 100) * a.n_personas);
  const dots = Array.from({ length: a.n_personas }, (_, i) => (i < yes ? "yes" : i < yes + maybe ? "maybe" : "no"));
  const quotes = a.quotes.filter((q) => q.would_buy !== "yes").slice(0, 1).concat(a.quotes.filter((q) => q.would_buy === "yes").slice(0, 1));

  return (
    <Link href="/test/demo" className="group block rounded-2xl bg-white p-5 text-slate-900 shadow-2xl ring-1 ring-white/20 transition hover:-translate-y-0.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Demo test{test.is_placeholder ? " · sample data" : ""}</p>
          <p className="mt-0.5 font-semibold">{a.product.name}</p>
          <p className="text-xs text-slate-500">{inr(a.product.price_inr)} · tested on {a.n_personas} AI customers</p>
        </div>
        <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-700 ring-1 ring-violet-200">AI-simulated</span>
      </div>

      <div className="mt-4 grid grid-cols-10 gap-1.5" aria-label={`${yes} would buy, ${maybe} maybe, ${a.n_personas - yes - maybe} would not`}>
        {dots.map((d, i) => (
          <span key={i} className={`aspect-square rounded-full ${d === "yes" ? "bg-emerald-500" : d === "maybe" ? "bg-amber-400" : "bg-slate-200"}`} />
        ))}
      </div>
      <div className="mt-2 flex gap-4 text-[11px] text-slate-500">
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" />Would buy</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-400" />Maybe</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-slate-300" />No</span>
      </div>

      <div className="mt-4 flex items-end gap-3">
        <p className="text-4xl font-semibold tabular-nums">{Math.round(a.overall.would_buy_pct)}%</p>
        <p className="pb-1 text-sm text-slate-600">would buy at {inr(a.product.price_inr)}</p>
      </div>
      {b && (
        <p className="mt-1 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          After one AI-suggested change (<strong>{inr(b.product.price_inr)}</strong>):{" "}
          <strong className="tabular-nums">{Math.round(b.overall.would_buy_pct)}%</strong> would buy
        </p>
      )}

      <div className="mt-4 space-y-2">
        {quotes.map((q) => (
          <figure key={q.persona_id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
            <blockquote className="text-slate-800">“{q.quote}”</blockquote>
            <figcaption className="mt-1 text-xs text-slate-500">
              {q.persona_name}{q.age ? `, ${q.age}` : ""}{q.city ? ` · ${q.city}` : ""} · {q.segment_name}
            </figcaption>
          </figure>
        ))}
      </div>
      <p className="mt-3 text-sm font-medium text-indigo-700 group-hover:underline">Open the full demo →</p>
    </Link>
  );
}
