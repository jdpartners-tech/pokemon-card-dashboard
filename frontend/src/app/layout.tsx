"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <html lang="en">
      <body className="min-h-screen text-gray-100" style={{ backgroundColor: "#06090e" }}>
        <div
          className="fixed inset-0 -z-10"
          style={{
            backgroundImage: "url(/backgrounds/pokemon-wheel-cover.png)",
            backgroundSize: "cover",
            backgroundPosition: "center center",
            backgroundRepeat: "no-repeat",
            filter: "brightness(0.45)",
          }}
        />

        {/* Nav */}
        <nav className="sticky top-0 z-50 border-b border-white/5"
             style={{ background: "rgba(8, 12, 20, 0.85)", backdropFilter: "blur(8px)" }}>
          <div className="max-w-7xl mx-auto px-4 h-12 flex items-center gap-6">
            <span className="font-bold text-sm text-gray-100 tracking-wide">
              PokéInvest
            </span>
            <div className="flex gap-4 ml-4">
              {[
                { href: "/", label: "Home" },
                { href: "/my-cards", label: "My Cards" },
                { href: "/watchlist", label: "Watchlist" },
              ].map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`text-sm transition-colors ${
                    pathname === href
                      ? "text-white font-semibold"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>
        </nav>

        {/* Page content */}
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
