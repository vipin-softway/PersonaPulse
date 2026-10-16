import Link from "next/link";
import type { ReactNode } from "react";
import NewTestLink from "./NewTestLink";

export const CHART = {
  // Categorical slots 1–2 from the validated reference palette (light surface).
  series1: "#2a78d6",
  series2: "#eb6834",
  ink: "#0f172a",
  muted: "#64748b",
  grid: "#e2e8f0",
};

export const inr = (n: number | null | undefined) =>
  n == null ? "–" : `₹${Math.round(n).toLocaleString("en-IN")}`;

export function SiteHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="font-semibold tracking-tight">
          Persona<span className="text-indigo-600">Pulse</span>
        </Link>
        <div className="flex items-center gap-4 text-sm text-slate-600">
          <Link href="/test/demo" className="hover:text-slate-900">Demo</Link>
          <Link href="/accuracy" className="hover:text-slate-900">Accuracy</Link>
          <NewTestLink className="rounded-md bg-indigo-600 px-3 py-1.5 font-medium text-white hover:bg-indigo-500">
            Run a test
          </NewTestLink>
        </div>
      </nav>
    </header>
  );
}

export function AiBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2.5 py-0.5 text-xs font-medium text-violet-700 ring-1 ring-violet-200">
      <span aria-hidden>✦</span> AI-simulated customers
    </span>
  );
}

export function Card({ title, subtitle, children, className = "" }: { title?: string; subtitle?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {title && <h2 className="text-base font-semibold text-slate-900">{title}</h2>}
      {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
      <div className={title || subtitle ? "mt-4" : ""}>{children}</div>
    </section>
  );
}

export function StatTile({ label, value, detail }: { label: string; value: string; detail?: ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-900 tabular-nums">{value}</p>
      {detail && <p className="mt-1 text-sm text-slate-600">{detail}</p>}
    </div>
  );
}

export function PlaceholderNotice({ what }: { what: string }) {
  return (
    <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
      Sample {what} for layout only. It will be replaced with a real Gemini run.
    </p>
  );
}

export function ErrorBox({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
      <p>{message}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 py-16 text-slate-500" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600" aria-hidden />
      {label}
    </div>
  );
}
