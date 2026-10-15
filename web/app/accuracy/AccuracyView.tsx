"use client";

import { useEffect, useState } from "react";
import { AccuracyScatter } from "@/components/charts";
import { AiBadge, Card, ErrorBox, PlaceholderNotice, Spinner, StatTile, inr } from "@/components/ui";
import { getBacktest } from "@/lib/api";
import type { Backtest } from "@/lib/types";

export default function AccuracyView() {
  const [data, setData] = useState<Backtest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getBacktest().then(setData).catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Spinner label="Loading back-test…" />;

  const { mae_model, mae_baseline } = data.metrics;
  const better = mae_baseline > 0 ? Math.round((1 - mae_model / mae_baseline) * 100) : 0;
  const baseline = data.products[0]?.baseline_rating ?? 0;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <AiBadge />
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">How accurate are the AI customers?</h1>
        <p className="max-w-3xl text-slate-700">
          We hid {data.n_holdout} {data.category.toLowerCase()} products, built personas only from reviews of the other products,
          then asked the personas to rate the hidden ones as if they were new launches. Here is how their predictions compare
          with the products&apos; real average ratings.
        </p>
      </div>
      {data.is_placeholder && <PlaceholderNotice what="back-test" />}

      <div className="grid gap-4 sm:grid-cols-3">
        <StatTile label="PersonaPulse error (MAE)" value={mae_model.toFixed(2)} detail="stars off, on average" />
        <StatTile label="Baseline error (MAE)" value={mae_baseline.toFixed(2)} detail={data.baseline_description} />
        <StatTile label="Improvement over baseline" value={`${better}%`} detail="lower prediction error" />
      </div>

      <Card title="Predicted vs. actual rating" subtitle="Each dot is a hidden product. Closer to the dashed diagonal is better.">
        <AccuracyScatter products={data.products} baseline={baseline} />
      </Card>

      <Card title="Hidden products">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr className="border-b border-slate-200">
                <th className="py-2 pr-4 font-medium">Product</th>
                <th className="py-2 pr-4 text-right font-medium">Price</th>
                <th className="py-2 pr-4 text-right font-medium">Predicted</th>
                <th className="py-2 pr-4 text-right font-medium">Actual</th>
                <th className="py-2 text-right font-medium">Error</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {data.products.map((p) => (
                <tr key={p.product_id} className="border-b border-slate-100">
                  <td className="py-2 pr-4 text-slate-900">{p.product_name}</td>
                  <td className="py-2 pr-4 text-right">{inr(p.price_inr)}</td>
                  <td className="py-2 pr-4 text-right">{p.predicted_rating.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-right">{p.actual_rating.toFixed(2)}</td>
                  <td className="py-2 text-right text-slate-600">{Math.abs(p.predicted_rating - p.actual_rating).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <p className="text-sm text-slate-500">
        Limitations: review writers skew to extremes, and predictions are weaker for categories with no similar products.
        PersonaPulse is a fast early filter before real-customer validation, not a replacement for it.
      </p>
    </div>
  );
}
