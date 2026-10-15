import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PersonaPulse – AI focus groups for small businesses",
  description:
    "Test a product concept on AI customer personas grounded in real reviews. Results are AI-simulated customers.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900">
        {children}
        <footer className="mt-auto border-t border-slate-200 py-4 text-center text-xs text-slate-500">
          All results are <strong>AI-simulated customers</strong>. Personas are built from public product review data.
        </footer>
      </body>
    </html>
  );
}
