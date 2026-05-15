"use client";

import { useState } from "react";
import { triggerScrape } from "@/lib/api";

export default function ScrapeTrigger() {
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");

  async function handleClick() {
    setStatus("running");
    try {
      await triggerScrape();
      setStatus("done");
      setTimeout(() => setStatus("idle"), 3000);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  }

  const label =
    status === "running" ? "Starting…" :
    status === "done" ? "Scrape started ✓" :
    status === "error" ? "Failed ✗" :
    "Run scrape now";

  return (
    <button
      onClick={handleClick}
      disabled={status === "running"}
      className={`px-3 py-1.5 text-sm rounded border transition-colors disabled:opacity-50 ${
        status === "done"
          ? "border-green-600 text-green-400"
          : status === "error"
          ? "border-red-600 text-red-400"
          : "border-gray-600 text-gray-300 hover:border-gray-400"
      }`}
    >
      {label}
    </button>
  );
}
