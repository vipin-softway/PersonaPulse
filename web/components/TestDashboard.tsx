"use client";

import { useState } from "react";
import { improveTest } from "@/lib/api";
import type { CountedText, Quote, Suggestion, TestResult, VariantResult } from "@/lib/types";
import { ComparisonChart, PriceChart, SegmentIntentChart } from "./charts";
import ProgressPanel from "./ProgressPanel";
import { AiBadge, Card, ErrorBox, PlaceholderNotice, StatTile, inr } from "./ui";

const variantLabel = (v: VariantResult) => (v.variant === "original" ? "Original" : `Variant ${v.variant.toUpperCase()}`);

export default function TestDashboard({ initial }: { initial: TestResult }) {
  const [test, setTest] = useState(initial);
  const [selected, setSelected] = useState(0);
  const v = test.variants[selected] ?? test.variants[0];

  return (
    <div className="space-y-6">
      <TestHeader test={test} v={v} />
      {test.is_placeholder && <PlaceholderNotice what="results" />}

      {test.variants.length > 1 && (
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Variant">
          {test.variants.map((x, i) => (
            <button
              key={x.variant}
              role="tab"
              aria-selected={i === selected}
              onClick={() => setSelected(i)}
              className={`rounded-full px-3 py-1.5 text-sm font-medium ring-1 ${
                i === selected ? "bg-slate-900 text-white ring-slate-900" : "bg-white text-slate-700 ring-slate-300 hover:bg-slate-50"
              }`}
            >
              {variantLabel(x)} · {inr(x.product.price_inr)}
            </button>
          ))}
        </div>
      )}

      <VariantView v={v} />

      <ImproveSection test={test} onUpdated={(t, idx) => { setTest(t); setSelected(idx); }} onSelect={setSelected} />
    </div>
  );
}

function TestHeader({ test, v }: { test: TestResult; v: VariantResult }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <AiBadge />
        {test.is_demo && <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">Demo test</span>}
      </div>
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{v.product.name}</h1>
      <p className="text-sm text-slate-600">
        {inr(v.product.price_inr)} · {v.product.pack_size} · {v.product.channel} · tested on {v.n_personas} AI customers
      </p>
      {v.product.description && <p className="max-w-3xl text-slate-700">{v.product.description}</p>}
    </div>
  );
}

function VariantView({ v }: { v: VariantResult }) {
  const best = [...v.segments].sort((a, b) => b.would_buy_pct - a.would_buy_pct)[0];
  const p = v.price;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatTile label="Would buy" value={`${Math.round(v.overall.would_buy_pct)}%`} detail={`of ${v.n_personas} AI customers`} />
        <StatTile
          label="Median willingness to pay"
          value={inr(p.median_wtp_inr)}
          detail={<>vs. your price {inr(p.price_inr)}</>}
        />
        <StatTile
          label="Strongest segment"
          value={best ? `${Math.round(best.would_buy_pct)}%` : "–"}
          detail={best?.segment_name}
        />
      </div>

      {v.insights && (
        <Card title="AI insights summary">
          <p className="text-lg font-medium text-slate-900">{v.insights.headline}</p>
          <p className="mt-2 text-slate-700">{v.insights.summary}</p>
          <div className="mt-4 grid gap-6 md:grid-cols-2">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Key findings</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {v.insights.key_findings.map((f) => <li key={f}>{f}</li>)}
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Recommendations</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {v.insights.recommendations.map((f) => <li key={f}>{f}</li>)}
              </ul>
            </div>
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        <Card title="Purchase intent by segment" subtitle="Share of each segment's AI customers who would buy" className="lg:col-span-3">
          <SegmentIntentChart segments={v.segments} />
        </Card>
        <Card title="Price insight" subtitle="What each AI customer would pay" className="lg:col-span-2">
          <PriceChart price={p} />
          {p.pct_wtp_at_or_above_price != null && (
            <p className="mt-3 text-sm text-slate-700">
              <strong className="tabular-nums">{Math.round(p.pct_wtp_at_or_above_price)}%</strong> would pay {inr(p.price_inr)} or more.
              {p.median_wtp_inr != null && p.median_wtp_inr < p.price_inr && (
                <> The typical customer expects around <strong>{inr(p.median_wtp_inr)}</strong>.</>
              )}
            </p>
          )}
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Top objections" subtitle="Share of AI customers raising each concern">
          <ThemeList items={v.top_objections} tone="rose" empty="No common objections." />
        </Card>
        <Card title="What they liked" subtitle="Share of AI customers mentioning each">
          <ThemeList items={v.top_likes} tone="emerald" empty="No common likes." />
        </Card>
      </div>

      <Card title="In their own words" subtitle="A mix of AI customers who would and wouldn't buy">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {v.quotes.map((q) => <QuoteCard key={q.persona_id} q={q} />)}
        </div>
      </Card>
    </div>
  );
}

function ThemeList({ items, tone, empty }: { items: CountedText[]; tone: "rose" | "emerald"; empty: string }) {
  if (!items.length) return <p className="text-sm text-slate-500">{empty}</p>;
  const bar = tone === "rose" ? "bg-rose-400" : "bg-emerald-500";
  const max = Math.max(...items.map((i) => i.pct));
  return (
    <ul className="space-y-3">
      {items.map((i) => (
        <li key={i.text}>
          <div className="flex justify-between gap-3 text-sm">
            <span className="text-slate-800">{i.text}</span>
            <span className="text-slate-500 tabular-nums">{Math.round(i.pct)}%</span>
          </div>
          <div className="mt-1 h-1.5 rounded-full bg-slate-100">
            <div className={`h-full rounded-full ${bar}`} style={{ width: `${(i.pct / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

function QuoteCard({ q }: { q: Quote }) {
  return (
    <figure className="flex h-full flex-col rounded-lg border border-slate-200 bg-slate-50 p-4">
      <span
        className={`self-start rounded-full px-2 py-0.5 text-xs font-medium ${
          q.would_buy ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
        }`}
      >
        {q.would_buy ? "✓ Would buy" : "✕ Wouldn't buy"}
      </span>
      <blockquote className="mt-3 flex-1 text-sm text-slate-800">“{q.quote}”</blockquote>
      <figcaption className="mt-3 text-xs text-slate-500">
        <span className="font-medium text-slate-700">{q.persona_name}</span>
        {q.age ? `, ${q.age}` : ""}
        {q.city ? ` · ${q.city}` : ""}
        <br />
        {q.segment_name}
      </figcaption>
    </figure>
  );
}

function ImproveSection({
  test,
  onUpdated,
  onSelect,
}: {
  test: TestResult;
  onUpdated: (t: TestResult, selectIdx: number) => void;
  onSelect: (idx: number) => void;
}) {
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const original = test.variants[0];
  const tested = test.variants.slice(1);
  const [compareIdx, setCompareIdx] = useState(0);
  const compare = tested[Math.min(compareIdx, tested.length - 1)];

  async function retest(s: Suggestion) {
    const existing = test.variants.findIndex((v) => v.variant === s.variant_id);
    if (existing >= 0) {
      setCompareIdx(existing - 1);
      onSelect(existing);
      return;
    }
    setError(null);
    setRunning(s.variant_id);
    try {
      const updated = await improveTest(test.test_id, s.variant_id);
      const idx = updated.variants.findIndex((v) => v.variant === s.variant_id);
      setCompareIdx(Math.max(0, idx - 1));
      onUpdated(updated, Math.max(0, idx));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retest failed. Please try again.");
    } finally {
      setRunning(null);
    }
  }

  if (!test.suggestions.length && !tested.length) return null;

  return (
    <div className="space-y-6">
      {test.suggestions.length > 0 && (
        <Card title="Improve & retest" subtitle="Suggested variants based on the objections above. Retest one on the same AI customers.">
          <div className="grid gap-4 md:grid-cols-2">
            {test.suggestions.map((s) => {
              const done = test.variants.some((v) => v.variant === s.variant_id);
              return (
                <div key={s.variant_id} className="flex flex-col rounded-lg border border-slate-200 p-4">
                  <p className="font-medium text-slate-900">{s.title}</p>
                  <ul className="mt-2 space-y-1 text-sm text-slate-700">
                    {s.changes.map((c) => <li key={c}>• {c}</li>)}
                  </ul>
                  <p className="mt-2 text-sm text-slate-500">{s.rationale}</p>
                  <button
                    onClick={() => retest(s)}
                    disabled={running !== null}
                    className="mt-4 self-start rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {done ? "View comparison" : running === s.variant_id ? "Retesting…" : "Retest this variant"}
                  </button>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {running && <ProgressPanel personas={original.n_personas} title="Retesting the improved variant" />}
      {error && <ErrorBox message={error} />}

      {compare && !running && (
        <Card title="Side-by-side comparison" subtitle="Same AI customers, original vs. improved variant">
          {tested.length > 1 && (
            <div className="mb-4 flex flex-wrap gap-2">
              {tested.map((t, i) => (
                <button key={t.variant} onClick={() => setCompareIdx(i)}
                  className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ${i === compareIdx ? "bg-slate-900 text-white ring-slate-900" : "ring-slate-300"}`}>
                  vs. {variantLabel(t)}
                </button>
              ))}
            </div>
          )}
          <div className="mb-6 grid gap-4 sm:grid-cols-3">
            <Delta label="Would buy" a={original.overall.would_buy_pct} b={compare.overall.would_buy_pct} fmt={(n) => `${Math.round(n)}%`} unit="pts" />
            <Delta label="Price" a={original.product.price_inr} b={compare.product.price_inr} fmt={inr} neutral />
            <Delta label="Median willingness to pay" a={original.price.median_wtp_inr ?? 0} b={compare.price.median_wtp_inr ?? 0} fmt={inr} neutral />
          </div>
          <ComparisonChart a={original} b={compare} />
        </Card>
      )}
    </div>
  );
}

function Delta({ label, a, b, fmt, unit, neutral }: { label: string; a: number; b: number; fmt: (n: number) => string; unit?: string; neutral?: boolean }) {
  const d = b - a;
  const color = neutral || d === 0 ? "text-slate-600" : d > 0 ? "text-emerald-700" : "text-rose-700";
  return (
    <div className="rounded-lg bg-slate-50 p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums text-slate-900">
        {fmt(a)} <span className="text-slate-400">→</span> {fmt(b)}
      </p>
      <p className={`text-sm tabular-nums ${color}`}>
        {d > 0 ? "▲ " : d < 0 ? "▼ " : "No change"}
        {d !== 0 && (unit ? `${Math.round(Math.abs(d))} ${unit}` : fmt(Math.abs(d)))}
      </p>
    </div>
  );
}
