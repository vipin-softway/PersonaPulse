import Link from "next/link";
import HealthStatus from "@/components/HealthStatus";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-8 px-4 py-20 text-center">
      <HealthStatus />
      <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">PersonaPulse</h1>
      <p className="max-w-xl text-lg text-slate-600">
        Test your product on 100 AI customers built from real reviews, and see who would buy it, at what price, and
        why not, in minutes instead of weeks.
      </p>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Link
          href="/test/demo"
          className="rounded-lg bg-indigo-600 px-5 py-3 font-medium text-white shadow-sm hover:bg-indigo-500"
        >
          View demo test
        </Link>
        <Link
          href="/test/new"
          className="rounded-lg border border-slate-300 bg-white px-5 py-3 font-medium text-slate-800 hover:bg-slate-100"
        >
          Run your own test
        </Link>
      </div>
      <Link href="/accuracy" className="text-sm text-indigo-700 underline-offset-4 hover:underline">
        How accurate is it? See the back-test →
      </Link>
    </main>
  );
}
