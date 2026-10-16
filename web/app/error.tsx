"use client"; // Error boundaries must be Client Components

import Link from "next/link";
import { useEffect } from "react";

/** Friendly fallback if anything on a page throws: judges never see a stack trace. */
export default function Error({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-4 px-4 py-24 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Something went wrong on this page</h1>
      <p className="text-slate-600">Please try again. The demo test always works if you want to look around.</p>
      <div className="flex gap-3">
        <button onClick={() => retry()} className="rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500">
          Try again
        </button>
        <Link href="/test/demo" className="rounded-lg border border-slate-300 bg-white px-4 py-2 font-medium text-slate-800 hover:bg-slate-100">
          View the demo test
        </Link>
      </div>
    </main>
  );
}
