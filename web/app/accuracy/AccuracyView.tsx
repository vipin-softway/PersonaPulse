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

  const m = data.metrics;
  const calibrated = m.mae_raw != null;
  const pairsPct = m.pairs_total ? Math.round((100 * (m.pairs_correct ?? 0)) / m.pairs_total) : null;
  const baseline = data.products[0]?.baseline_rating ?? 0;
  const chartProducts = data.products.map((p) => ({ ...p, predicted_rating: p.calibrated_rating ?? p.predicted_rating }));

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <AiBadge />
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">How accurate are the AI customers?</h1>
        <p className="max-w-3xl text-slate-700">
          We hid {data.n_holdout} products from the {data.category.toLowerCase()} category, built personas only from reviews of the
          other products, then asked {data.n_personas ? `all ${data.n_personas} ` : ""}personas to rate the hidden ones as if they
          had bought them{data.n_predictions ? ` (${data.n_predictions.toLocaleString("en-IN")} predictions)` : ""}. They saw only
          each product&apos;s name, description and price, never its reviews or rating.
        </p>
      </div>
      {data.is_placeholder && <PlaceholderNotice what="back-test" />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {pairsPct != null ? (
          <StatTile label="Ranks products correctly" value={`${pairsPct}%`}
            detail={`${m.pairs_correct} of ${m.pairs_total} product pairs ordered the same way as real buyers`} />
        ) : (
          <StatTile label="Correlation" value={m.correlation != null ? m.correlation.toFixed(2) : "–"} detail="predicted vs. actual" />
        )}
        <StatTile label={calibrated ? "Error after calibration" : "PersonaPulse error (MAE)"} value={`${m.mae_model.toFixed(2)}★`}
          detail={`vs. ${m.mae_baseline.toFixed(2)}★ for the baseline`} />
        <StatTile label="Correlation" value={m.correlation != null ? m.correlation.toFixed(2) : "–"}
          detail="predicted vs. actual ratings across hidden products" />
        {m.complaint_total ? (
          <StatTile label="Real complaints predicted" value={`${m.complaint_hits ?? 0} of ${m.complaint_total}`}
            detail="top real complaints that appeared in the AI customers' top 5" />
        ) : null}
      </div>

      {calibrated && m.bias != null && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-700 shadow-sm">
          <p className="font-medium text-slate-900">What this means</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>
              <strong>The AI customers are stricter than Amazon reviewers</strong>: their raw ratings are{" "}
              {Math.abs(m.bias).toFixed(1)}★ lower on average (raw error {m.mae_raw?.toFixed(2)}★). Online star ratings skew
              high, and our personas are told not to be positive by default.
            </li>
            <li>
              <strong>They still rank products well.</strong> In {pairsPct}% of product pairs they preferred the one real buyers
              rated higher. That is what a launch decision needs: is version A better than version B? A constant baseline
              can&apos;t rank products at all.
            </li>
            <li>
              <strong>Calibrated error:</strong> shifting each prediction by the average offset measured on the <em>other</em>{" "}
              hidden products (so no product&apos;s own rating is used) gives {m.mae_model.toFixed(2)}★, against{" "}
              {m.mae_baseline.toFixed(2)}★ for always guessing the category average.
            </li>
          </ul>
        </div>
      )}

      <Card title="Predicted vs. actual rating"
        subtitle={calibrated ? "Each dot is a hidden product (calibrated prediction). Closer to the dashed diagonal is better." : "Each dot is a hidden product. Closer to the dashed diagonal is better."}>
        <AccuracyScatter products={chartProducts} baseline={baseline} />
      </Card>

      <Card title="Hidden products">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr className="border-b border-slate-200">
                <th className="py-2 pr-4 font-medium">Product</th>
                <th className="py-2 pr-4 text-right font-medium">Price</th>
                <th className="py-2 pr-4 text-right font-medium">Raw prediction</th>
                <th className="py-2 pr-4 text-right font-medium">Calibrated</th>
                <th className="py-2 pr-4 text-right font-medium">Actual</th>
                <th className="py-2 pr-4 text-right font-medium">Error (calibrated)</th>
                <th className="py-2 text-right font-medium">Complaints matched</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {data.products.map((p) => (
                <tr key={p.product_id} className="border-b border-slate-100">
                  <td className="py-2 pr-4 text-slate-900">{p.product_name}</td>
                  <td className="py-2 pr-4 text-right">{inr(p.price_inr)}</td>
                  <td className="py-2 pr-4 text-right text-slate-500">{p.predicted_rating.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-right">{(p.calibrated_rating ?? p.predicted_rating).toFixed(2)}</td>
                  <td className="py-2 pr-4 text-right">{p.actual_rating.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-right text-slate-600">
                    {Math.abs((p.calibrated_rating ?? p.predicted_rating) - p.actual_rating).toFixed(2)}
                  </td>
                  <td className="py-2 text-right text-slate-600">
                    {p.complaint_total ? `${p.complaint_hits} of ${p.complaint_total}` : "–"}
                  </td>
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
