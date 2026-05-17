// frontend/src/app/layout.tsx
"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname } from "next/navigation";

const BG_MAP: Record<string, string> = {
  "/":           "/backgrounds/home.jpg",
  "/card":       "/backgrounds/detail.jpg",
  "/my-cards":   "/backgrounds/my-cards.jpg",
  "/watchlist":  "/backgrounds/watchlist.jpg",
};

function getBackground(pathname: string): string {
  if (pathname.startsWith("/card/")) return BG_MAP["/card"];
  return BG_MAP[pathname] ?? BG_MAP["/"];
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const bg = getBackground(pathname);

  return (
    <html lang="en">
      <body className="min-h-screen text-gray-100" style={{ backgroundColor: "#080c14" }}>
        {/* Full-bleed background */}
        <div
          className="fixed inset-0 -z-10 bg-cover bg-center"
          style={{
            backgroundImage: `url(${bg})`,
            filter: "brightness(0.18)",
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
