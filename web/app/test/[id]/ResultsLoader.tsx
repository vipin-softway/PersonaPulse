"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import TestDashboard from "@/components/TestDashboard";
import { ErrorBox, Spinner } from "@/components/ui";
import { getTest } from "@/lib/api";
import type { TestResult } from "@/lib/types";

export default function ResultsLoader() {
  const { id } = useParams<{ id: string }>();
  const [test, setTest] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    getTest(id).then(setTest).catch((e: Error) => setError(e.message));
  }, [id, attempt]);

  function retry() {
    setError(null);
    setAttempt((n) => n + 1);
  }

  if (error)
    return (
      <ErrorBox
        message={error}
        action={
          <div className="flex gap-3">
            <button onClick={retry} className="rounded-md bg-white px-3 py-1.5 font-medium ring-1 ring-rose-300 hover:bg-rose-100">Try again</button>
            {id !== "demo" && <Link href="/test/demo" className="rounded-md px-3 py-1.5 font-medium underline">View the demo test instead</Link>}
          </div>
        }
      />
    );
  if (!test) return <Spinner label={id === "demo" ? "Loading the demo test…" : "Loading results…"} />;
  return <TestDashboard initial={test} />;
}
