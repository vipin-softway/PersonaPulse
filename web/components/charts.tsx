"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { useSyncExternalStore } from "react";
import type { BacktestProduct, PriceInsight, SegmentResult, VariantResult } from "@/lib/types";
import { CHART, inr } from "./ui";

const axisTick = { fill: CHART.muted, fontSize: 12 };

const NARROW = "(max-width: 640px)";
/** Width of the category-label column on horizontal bar charts; narrower on phones. */
function useLabelWidth() {
  const narrow = useSyncExternalStore(
    (cb) => {
      const mq = window.matchMedia(NARROW);
      mq.addEventListener("change", cb);
      return () => mq.removeEventListener("change", cb);
    },
    () => window.matchMedia(NARROW).matches,
    () => false,
  );
  return { width: narrow ? 100 : 170, fontSize: narrow ? 11 : 12 };
}

function TipBox({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 shadow-md">{children}</div>;
}

/** Would-buy % per segment for one variant. */
export function SegmentIntentChart({ segments }: { segments: SegmentResult[] }) {
  const lw = useLabelWidth();
  const data = segments.map((s) => ({ ...s, label: s.segment_name }));
  return (
    <div style={{ height: Math.max(180, data.length * 52) }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 40, bottom: 0, left: 0 }} barCategoryGap={10}>
          <CartesianGrid horizontal={false} stroke={CHART.grid} />
          <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={axisTick} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="label" width={lw.width} tick={{ ...axisTick, fontSize: lw.fontSize, fill: CHART.ink }} axisLine={false} tickLine={false} />
          <Tooltip
            cursor={{ fill: "#f1f5f9" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const s = payload[0].payload as SegmentResult;
              return (
                <TipBox>
                  <p className="font-medium text-slate-900">{s.segment_name}</p>
                  <p>{Math.round(s.would_buy_pct)}% yes · {Math.round(s.maybe_pct)}% maybe · {Math.round(s.no_pct)}% no</p>
                  <p>{s.n} AI customers</p>
                  <p>Median willingness to pay {inr(s.median_wtp_inr)}</p>
                </TipBox>
              );
            }}
          />
          <Bar dataKey="would_buy_pct" fill={CHART.series1} radius={[0, 4, 4, 0]} maxBarSize={26} isAnimationActive={false}>
            <LabelList dataKey="would_buy_pct" position="right" formatter={(v) => `${Math.round(Number(v))}%`} style={{ fill: CHART.ink, fontSize: 12 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Original vs. variant would-buy % per segment. */
export function ComparisonChart({ a, b }: { a: VariantResult; b: VariantResult }) {
  const lw = useLabelWidth();
  const bySeg = new Map(b.segments.map((s) => [s.segment_id, s]));
  const data = a.segments.map((s) => ({
    label: s.segment_name,
    a: s.would_buy_pct,
    b: bySeg.get(s.segment_id)?.would_buy_pct ?? 0,
  }));
  const nameA = `Original · ${inr(a.product.price_inr)}`;
  const nameB = `${b.variant.toUpperCase()} · ${inr(b.product.price_inr)}`;
  return (
    <div style={{ height: Math.max(220, data.length * 64) }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 40, bottom: 0, left: 0 }} barCategoryGap={12} barGap={2}>
          <CartesianGrid horizontal={false} stroke={CHART.grid} />
          <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={axisTick} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="label" width={lw.width} tick={{ ...axisTick, fontSize: lw.fontSize, fill: CHART.ink }} axisLine={false} tickLine={false} />
          <Tooltip
            cursor={{ fill: "#f1f5f9" }}
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <TipBox>
                  <p className="font-medium text-slate-900">{label}</p>
                  <p>{nameA}: {payload[0]?.value}% would buy</p>
                  <p>{nameB}: {payload[1]?.value}% would buy</p>
                </TipBox>
              ) : null
            }
          />
          <Legend verticalAlign="top" align="left" iconType="square" wrapperStyle={{ fontSize: 12, paddingBottom: 8, color: CHART.ink }} />
          <Bar name={nameA} dataKey="a" fill={CHART.series1} radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false}>
            <LabelList dataKey="a" position="right" formatter={(v) => `${Math.round(Number(v))}%`} style={{ fill: CHART.muted, fontSize: 11 }} />
          </Bar>
          <Bar name={nameB} dataKey="b" fill={CHART.series2} radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false}>
            <LabelList dataKey="b" position="right" formatter={(v) => `${Math.round(Number(v))}%`} style={{ fill: CHART.ink, fontSize: 11 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Distribution of willingness to pay, with the asking price marked. */
export function PriceChart({ price }: { price: PriceInsight }) {
  const data = price.buckets.map((b) => ({ ...b, label: `${inr(b.from_inr)}–${Math.round(b.to_inr)}` }));
  return (
    <div>
    <div className="h-56">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 20, right: 8, bottom: 0, left: -20 }} barCategoryGap={2}>
          <CartesianGrid vertical={false} stroke={CHART.grid} />
          <XAxis dataKey="label" tick={{ ...axisTick, fontSize: 11 }} axisLine={{ stroke: CHART.grid }} tickLine={false} interval={0} />
          <YAxis allowDecimals={false} tick={axisTick} axisLine={false} tickLine={false} />
          <Tooltip
            cursor={{ fill: "#f1f5f9" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const b = payload[0].payload as (typeof data)[number];
              return (
                <TipBox>
                  <p>{b.count} personas would pay {inr(b.from_inr)}–{inr(b.to_inr)}</p>
                </TipBox>
              );
            }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {data.map((b) => (
              <Cell key={b.from_inr} fill={b.from_inr >= price.price_inr ? CHART.series1 : "#b7d3f6"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-600">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: "#b7d3f6" }} />Below your price</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: CHART.series1 }} />{inr(price.price_inr)} or more</span>
      </div>
    </div>
  );
}

/** Predicted vs. actual rating on hidden products; dashed diagonal = perfect prediction. */
export function AccuracyScatter({ products, baseline }: { products: BacktestProduct[]; baseline: number }) {
  const lo = Math.floor(Math.min(...products.flatMap((p) => [p.actual_rating, p.predicted_rating]), baseline) * 2) / 2 - 0.5;
  const domain: [number, number] = [Math.max(1, lo), 5];
  return (
    <div className="h-80">
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 10, right: 16, bottom: 24, left: 0 }}>
          <CartesianGrid stroke={CHART.grid} />
          <XAxis type="number" dataKey="actual_rating" name="Actual" domain={domain} tick={axisTick} tickCount={6}
            label={{ value: "Actual average rating (real reviews)", position: "bottom", offset: 8, fill: CHART.muted, fontSize: 12 }} />
          <YAxis type="number" dataKey="predicted_rating" name="Predicted" domain={domain} tick={axisTick} tickCount={6}
            label={{ value: "Predicted", angle: -90, position: "insideLeft", offset: 16, fill: CHART.muted, fontSize: 12 }} />
          <ReferenceLine segment={[{ x: domain[0], y: domain[0] }, { x: 5, y: 5 }]} stroke={CHART.muted} strokeDasharray="4 3"
            label={{ value: "Perfect prediction", position: "insideTopLeft", fill: CHART.muted, fontSize: 11 }} />
          <ReferenceLine y={baseline} stroke={CHART.series2} strokeDasharray="6 4"
            label={{ value: `Baseline ${baseline.toFixed(1)}`, position: "insideBottomRight", fill: CHART.ink, fontSize: 11 }} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload as BacktestProduct;
              return (
                <TipBox>
                  <p className="font-medium text-slate-900">{p.product_name}</p>
                  <p>Predicted {p.predicted_rating.toFixed(2)} · Actual {p.actual_rating.toFixed(2)}</p>
                  <p>{inr(p.price_inr)}</p>
                </TipBox>
              );
            }}
          />
          <ZAxis range={[110, 110]} />
          <Scatter data={products} fill={CHART.series1} stroke="#fff" strokeWidth={2} shape="circle" isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
