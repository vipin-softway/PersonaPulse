"use client";

import Link from "next/link";
import type { ReactNode } from "react";

export const NEW_TEST_EVENT = "personapulse:new-test";

/** Link to the test form. Clicking it while already on the form (same URL, no remount) tells the form to reset. */
export default function NewTestLink({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <Link href="/test/new" className={className} onClick={() => window.dispatchEvent(new Event(NEW_TEST_EVENT))}>
      {children}
    </Link>
  );
}
