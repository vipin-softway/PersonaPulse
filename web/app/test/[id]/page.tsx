import { Suspense } from "react";
import ResultsLoader from "./ResultsLoader";
import { Spinner } from "@/components/ui";

export default function TestPage() {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
      <Suspense fallback={<Spinner label="Loading results…" />}>
        <ResultsLoader />
      </Suspense>
    </main>
  );
}
