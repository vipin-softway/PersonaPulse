import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-4 px-4 py-24 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">We couldn&apos;t find that page</h1>
      <p className="text-slate-600">It may have moved. Start from the demo test or run your own.</p>
      <div className="flex gap-3">
        <Link href="/test/demo" className="rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500">
          View the demo test
        </Link>
        <Link href="/test/new" className="rounded-lg border border-slate-300 bg-white px-4 py-2 font-medium text-slate-800 hover:bg-slate-100">
          Run a test
        </Link>
      </div>
    </main>
  );
}
