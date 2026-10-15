import Link from "next/link";
import type { ReactNode } from "react";
import HealthStatus from "@/components/HealthStatus";
import HeroPreview from "@/components/HeroPreview";
import { PANELS, type PanelId } from "@/lib/panels";

const ICONS: Record<PanelId, ReactNode> = {
  accessories: <path d="M9 3v4M15 3v4M7 7h10v4a5 5 0 0 1-10 0V7ZM12 16v5" />,
  home: <path d="M3 11 12 4l9 7M5 10v10h14V10M10 20v-5h4v5" />,
  electronics: <path d="M9 3h6l1 4H8l1-4ZM9 21h6l1-4H8l1 4ZM7 7h10v10H7zM12 10v2.5l1.5 1" />,
};

const PANEL_EXAMPLES: Record<PanelId, string[]> = {
  accessories: ["Fast-charging cable", "Wireless earbuds", "Power bank"],
  home: ["Personal air cooler", "Mixer grinder", "Electric kettle"],
  electronics: ["Smartwatch", "Smart TV", "Bluetooth speaker"],
};

const COSTS = [
  { title: "Research is slow and expensive", body: "Surveys and focus groups take weeks and agency budgets, so most small businesses skip them entirely." },
  { title: "So launches run on gut feel", body: "One price, one pack, one message, decided in a meeting. Nobody hears from the customers who will say no." },
  { title: "And mistakes land in the warehouse", body: "A launch that misses means unsold stock, wasted ad spend and shelf space that should have gone to a winner." },
];

const COMPARE: [string, string, string][] = [
  ["Time to an answer", "Weeks", "About a minute"],
  ["Cost per test", "Agency budgets", "Rupees of AI compute"],
  ["Who you hear from", "A dozen people in one city", "AI customers across segments, cities and incomes"],
  ["Trying a new price or pack", "Start another study", "Change it and retest the same customers"],
  ["Knowing if it's accurate", "Hard to tell", "Back-tested on products it has never seen"],
];

const OUTCOMES = [
  { verb: "Understand", what: "who your customers are and why they say no", how: "Segments, objections and quotes from AI customers grounded in real reviews" },
  { verb: "Engage", what: "each segment with the right price and message", how: "Willingness to pay and purchase intent per segment" },
  { verb: "Serve", what: "them a product they actually want", how: "AI-suggested variants, retested on the same customers" },
  { verb: "Run leaner", what: "with fewer failed launches", how: "Filter weak ideas before you buy stock, list or advertise" },
];

const STEPS: { title: string; body: string; tech: string[] }[] = [
  { title: "Real shopper reviews", body: "6,800+ Amazon India reviews, cleaned and stored, grouped into three category panels.", tech: ["BigQuery"] },
  { title: "What drives each buyer", body: "Every review becomes structured signals: priorities, complaints, price sensitivity, dealbreakers.", tech: ["BigQuery AI", "Gemini Flash"] },
  { title: "Segments and AI customers", body: "Gemini finds how each panel decides to buy, then creates personas whose memories are real reviews.", tech: ["Gemini Pro"] },
  { title: "Your product, tested live", body: "Each AI customer reacts on its own, in parallel: buy or not, at what price, and why.", tech: ["Gemini on Vertex AI", "Cloud Run", "Cloud Storage"] },
  { title: "Insights and a better version", body: "A plain-English report, then concrete changes you can retest in one click.", tech: ["Gemini Pro", "BigQuery"] },
];

export default function Home() {
  return (
    <main className="flex-1">
      {/* Hero */}
      <section className="relative overflow-hidden bg-slate-950 text-white">
        <div className="pointer-events-none absolute -top-40 left-1/2 h-[480px] w-[900px] -translate-x-1/2 rounded-full bg-indigo-600/30 blur-3xl" aria-hidden />
        <div className="relative mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:py-20 lg:grid-cols-[1.15fr_1fr] lg:items-center">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-indigo-200 ring-1 ring-white/15">
                Retail &amp; Commerce · AI customer intelligence
              </span>
              <HealthStatus />
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight sm:text-5xl">
              Every launch is a bet.
              <br />
              <span className="bg-gradient-to-r from-indigo-300 to-violet-300 bg-clip-text text-transparent">Stop betting blind.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-300">
              Most new products fail, and small businesses find out only after paying for stock, listings and ads.
              PersonaPulse puts your idea in front of AI customers built from real shopper reviews and tells you who will buy,
              at what price, and what to change, in about a minute.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/test/new" className="rounded-lg bg-indigo-500 px-5 py-3 text-center font-medium text-white shadow-lg shadow-indigo-500/30 hover:bg-indigo-400">
                Test your product now
              </Link>
              <Link href="/test/demo" className="rounded-lg bg-white/10 px-5 py-3 text-center font-medium text-white ring-1 ring-white/20 hover:bg-white/15">
                See a finished test
              </Link>
            </div>
            <dl className="mt-10 grid max-w-lg grid-cols-3 gap-4 border-t border-white/10 pt-6">
              <div><dt className="text-xs text-slate-400">Real reviews</dt><dd className="text-2xl font-semibold">6,800+</dd></div>
              <div><dt className="text-xs text-slate-400">Shopper panels</dt><dd className="text-2xl font-semibold">3</dd></div>
              <div><dt className="text-xs text-slate-400">Time per test</dt><dd className="text-2xl font-semibold">~1 min</dd></div>
            </dl>
          </div>
          <HeroPreview />
        </div>
      </section>

      {/* The business problem */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">The problem</p>
        <h2 className="mt-2 max-w-2xl text-3xl font-semibold tracking-tight">Guessing is the most expensive research there is</h2>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {COSTS.map((c, i) => (
            <div key={c.title} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <span className="text-sm font-semibold text-rose-600">0{i + 1}</span>
              <h3 className="mt-2 text-lg font-semibold text-slate-900">{c.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{c.body}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-5 py-3 font-medium text-slate-500" />
                  <th className="px-5 py-3 font-medium text-slate-500">Traditional research</th>
                  <th className="px-5 py-3 font-semibold text-indigo-700">PersonaPulse</th>
                </tr>
              </thead>
              <tbody>
                {COMPARE.map(([label, old, now]) => (
                  <tr key={label} className="border-b border-slate-100 last:border-0">
                    <td className="px-5 py-3 font-medium text-slate-800">{label}</td>
                    <td className="px-5 py-3 text-slate-500">{old}</td>
                    <td className="px-5 py-3 font-medium text-slate-900">{now}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Outcomes, mapped to the track */}
      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">What changes</p>
          <h2 className="mt-2 max-w-2xl text-3xl font-semibold tracking-tight">From customer insight to a leaner launch</h2>
          <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {OUTCOMES.map((o) => (
              <div key={o.verb} className="rounded-xl bg-slate-50 p-5">
                <p className="text-2xl font-semibold text-indigo-600">{o.verb}</p>
                <p className="mt-1 font-medium text-slate-900">{o.what}</p>
                <p className="mt-2 text-sm text-slate-600">{o.how}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Panels */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">Try it</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight">Choose who tests your product</h2>
        <p className="mt-2 max-w-2xl text-slate-600">
          Each panel is its own crowd of AI customers, built only from reviews in that category, so a cooler is judged by
          appliance shoppers and a cable by accessory shoppers.
        </p>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {PANELS.map((p) => (
            <Link key={p.id} href={`/test/new?panel=${p.id}`}
              className="group flex flex-col rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md">
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

      {/* How it works */}
      <section className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">Under the hood</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight">Built on real data, running on Google Cloud</h2>
          <ol className="mt-8 grid gap-4 md:grid-cols-5">
            {STEPS.map((s, i) => (
              <li key={s.title} className="flex flex-col rounded-xl border border-slate-200 p-5">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white">{i + 1}</span>
                <h3 className="mt-3 font-semibold text-slate-900">{s.title}</h3>
                <p className="mt-1 flex-1 text-sm text-slate-600">{s.body}</p>
                <ul className="mt-3 flex flex-wrap gap-1.5">
                  {s.tech.map((t) => (
                    <li key={t} className="rounded bg-sky-50 px-2 py-0.5 text-[11px] font-medium text-sky-800 ring-1 ring-sky-200">{t}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Proof + final CTA */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl bg-slate-900 p-8 text-white">
            <p className="text-sm font-semibold uppercase tracking-wide text-indigo-300">Proof, not promises</p>
            <h2 className="mt-2 text-2xl font-semibold">We test our own accuracy</h2>
            <p className="mt-2 text-slate-300">
              We hid real products from the AI customers, asked them to rate those products as new launches, and compared the
              predictions with real ratings and a simple baseline.
            </p>
            <Link href="/accuracy" className="mt-6 inline-block rounded-lg bg-white px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-100">
              See the back-test
            </Link>
          </div>
          <div className="rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 p-8 text-white">
            <p className="text-sm font-semibold uppercase tracking-wide text-indigo-100">Before you spend on stock</p>
            <h2 className="mt-2 text-2xl font-semibold">Test your next idea in a minute</h2>
            <p className="mt-2 text-indigo-100">No login, no setup. Describe a product, pick a panel, and hear from AI customers.</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/test/new" className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50">
                Run a test
              </Link>
              <Link href="/test/demo" className="rounded-lg px-4 py-2 text-sm font-medium text-white ring-1 ring-white/40 hover:bg-white/10">
                View demo
              </Link>
            </div>
          </div>
        </div>
        <p className="mt-10 text-center text-xs text-slate-500">
          PersonaPulse is a fast early filter before real-customer validation, not a replacement for it.
        </p>
      </section>
    </main>
  );
}
