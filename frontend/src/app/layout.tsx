import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import ScrapeTrigger from "@/components/ScrapeTrigger";
import { reportUrl } from "@/lib/api";

export const metadata: Metadata = {
  title: "Pokemon Card Dashboard",
  description: "PSA 10 profitability research tool",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="bg-gray-950 text-gray-100">
      <body className="min-h-screen">
        <header className="border-b border-gray-800 bg-gray-900">
          <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
            <div className="flex items-center gap-6">
              <Link href="/" className="font-bold text-gray-100 hover:text-white">
                🃏 PSA10 Tracker
              </Link>
              <nav className="flex gap-5 text-sm text-gray-400">
                <Link href="/" className="hover:text-gray-200 transition-colors">
                  Cards
                </Link>
                <Link href="/watchlist" className="hover:text-gray-200 transition-colors">
                  Watchlist
                </Link>
              </nav>
            </div>
            <div className="flex items-center gap-3">
              <a
                href={reportUrl}
                download
                className="px-3 py-1.5 text-sm rounded border border-gray-600 text-gray-300 hover:border-gray-400 transition-colors"
              >
                ↓ CSV report
              </a>
              <ScrapeTrigger />
            </div>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
