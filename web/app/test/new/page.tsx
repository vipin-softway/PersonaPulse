import { Suspense } from "react";
import NewTestForm from "./NewTestForm";

export default function NewTestPage() {
  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Test a product concept</h1>
      <p className="mt-1 text-slate-600">
        Describe your product and up to 30 AI customers, built from real product reviews, will tell you whether they&apos;d buy it and why.
      </p>
      <p className="mt-2 text-sm text-slate-500">
        Three customer panels are available: electronics accessories, home &amp; kitchen appliances and consumer electronics.
        Results are most reliable for products in one of these categories.
      </p>
      <div className="mt-6">
        <Suspense>
          <NewTestForm />
        </Suspense>
      </div>
    </main>
  );
}
