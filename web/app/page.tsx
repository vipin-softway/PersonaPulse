import Link from "next/link";
import type { ReactNode } from "react";
import HealthStatus from "@/components/HealthStatus";
import { AiBadge } from "@/components/ui";
import { PANELS, type PanelId } from "@/lib/panels";

const ICONS: Record<PanelId, ReactNode> = {
  // Cable plug
  accessories: <path d="M9 3v4M15 3v4M7 7h10v4a5 5 0 0 1-10 0V7ZM12 16v5" />,
  // House
  home: <path d="M3 11 12 4l9 7M5 10v10h14V10M10 20v-5h4v5" />,
  // Smartwatch
  electronics: <path d="M9 3h6l1 4H8l1-4ZM9 21h6l1-4H8l1 4ZM7 7h10v10H7zM12 10v2.5l1.5 1" />,
};

const PANEL_EXAMPLES: Record<PanelId, string[]> = {
  accessories: ["Fast-charging cable", "Wireless earbuds", "Power bank"],
  home: ["Personal air cooler", "Mixer grinder", "Electric kettle"],
  electronics: ["Smartwatch", "Smart TV", "Bluetooth speaker"],
};

const QUESTIONS = [
  { q: "Who will buy it?", a: "Purchase intent for each customer segment, so you know who to target first.", tag: "Customer segmentation" },
  { q: "At what price?", a: "What each AI customer would pay, set against your price.", tag: "Pricing insight" },
  { q: "Why not?", a: "The objections that stop each segment, in their own words.", tag: "Customer insights" },
  { q: "What should I change?", a: "Gemini suggests better variants and retests them on the same customers.", tag: "Improve & retest" },
];

const STEPS = [
  { title: "Real reviews", body: "Thousands of Amazon India reviews are loaded into BigQuery and grouped into three shopper panels." },
  { title: "AI customers", body: "Gemini finds how each panel decides to buy, then creates personas whose memories are real reviews." },
  { title: "Your product", body: "Every AI customer reacts on its own: would they buy, at what price, and what puts them off." },
  { title: "Decide faster", body: "See results by segment, read the AI summary, and retest an improved version in about a minute." },
];

export default function Home() {
  return (
    <main className="flex-1">
      {/* Hero */}
      <section className="border-b border-slate-200 bg-gradient-to-b from-indigo-50 to-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-indigo-700 ring-1 ring-indigo-200">
              Retail &amp; Commerce · Customer insights
            </span>
            <HealthStatus />
          </div>
          <h1 className="mt-6 max-w-3xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
            Know how customers will react <span className="text-indigo-600">before you launch.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-slate-600">
            PersonaPulse is a self-serve AI focus group for small businesses. Test a product, price or pack on AI customers built
            from real reviews, see who would buy and why, then improve it and retest in minutes, not weeks.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/test/demo" className="rounded-lg bg-indigo-600 px-5 py-3 text-center font-medium text-white shadow-sm hover:bg-indigo-500">
              View demo test
            </Link>
            <Link href="/test/new" className="rounded-lg border border-slate-300 bg-white px-5 py-3 text-center font-medium text-slate-800 hover:bg-slate-100">
              Run your own test
            </Link>
          </div>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-600">
            <AiBadge />
            <span>Built from 6,800+ real product reviews</span>
            <span>3 shopper panels</span>
            <span>
              <Link href="/accuracy" className="text-indigo-700 underline-offset-4 hover:underline">Back-tested on hidden products →</Link>
            </span>
          </div>
        </div>
      </section>

      {/* Panels */}
      <section className="mx-auto max-w-6xl px-4 py-14">
        <h2 className="text-2xl font-semibold tracking-tight">Choose who tests your product</h2>
        <p className="mt-2 max-w-2xl text-slate-600">
          Each panel is a separate crowd of AI customers, built only from reviews in its category, so a cooler is judged by
          appliance shoppers and a cable by accessory shoppers.
        </p>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {PANELS.map((p) => (
            <Link key={p.id} href={`/test/new?panel=${p.id}`}
              className="group flex flex-col rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-indigo-300 hover:shadow-md">
              <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  {ICONS[p.id]}
                </svg>
              </span>
              <h3 className="mt-4 text-lg font-semibold text-slate-900">{p.label}</h3>
              <p className="text-sm text-slate-500">{p.shoppers}</p>
              <ul className="mt-4 flex flex-wrap gap-2">
                {PANEL_EXAMPLES[p.id].map((x) => (
                  <li key={x} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700">{x}</li>
                ))}
              </ul>
              <span className="mt-6 text-sm font-medium text-indigo-700 group-hover:underline">Test a product here →</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Questions answered */}
      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-14">
          <h2 className="text-2xl font-semibold tracking-tight">The four questions every launch needs answered</h2>
          <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {QUESTIONS.map((x) => (
              <div key={x.q}>
                <span className="text-xs font-medium uppercase tracking-wide text-indigo-600">{x.tag}</span>
                <h3 className="mt-1 text-lg font-semibold text-slate-900">{x.q}</h3>
                <p className="mt-1 text-sm text-slate-600">{x.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-4 py-14">
        <h2 className="text-2xl font-semibold tracking-tight">How it works</h2>
        <ol className="mt-8 grid gap-6 md:grid-cols-4">
          {STEPS.map((s, i) => (
            <li key={s.title} className="relative rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white">{i + 1}</span>
              <h3 className="mt-3 font-semibold text-slate-900">{s.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{s.body}</p>
            </li>
          ))}
        </ol>
        <div className="mt-10 flex flex-col items-start justify-between gap-4 rounded-xl bg-slate-900 p-6 text-white sm:flex-row sm:items-center">
          <div>
            <p className="font-semibold">Proof, not just promises</p>
            <p className="mt-1 text-sm text-slate-300">
              We hid real products from the AI customers, then asked them to rate those products. See how close they got.
            </p>
          </div>
          <Link href="/accuracy" className="shrink-0 rounded-lg bg-white px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-100">
            See the back-test
          </Link>
        </div>
        <p className="mt-8 text-center text-xs text-slate-500">
          Powered by Gemini on Vertex AI · BigQuery · Cloud Run
        </p>
      </section>
    </main>
  );
}
