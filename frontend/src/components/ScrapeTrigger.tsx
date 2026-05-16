"use client";

import { useState } from "react";
import { triggerScrape } from "@/lib/api";

type Status = "idle" | "running" | "done" | "error" | "disabled";

export default function ScrapeTrigger() {
  const [status, setStatus] = useState<Status>("idle");

  async function handleClick() {
    if (status === "disabled") return;
    setStatus("running");
    try {
      await triggerScrape();
      setStatus("done");
      setTimeout(() => setStatus("idle"), 3000);
    } catch (err: unknown) {
      // 503 means scraping is disabled on this deployment
      const is503 = err instanceof Error && err.message.startsWith("503");
      if (is503) {
        setStatus("disabled");
      } else {
        setStatus("error");
        setTimeout(() => setStatus("idle"), 3000);
      }
    }
  }

  if (status === "disabled") {
    return (
      <span className="px-3 py-1.5 text-sm text-gray-600 border border-gray-800 rounded">
        Scraping disabled
      </span>
    );
  }

  const label =
    status === "running" ? "Starting…" :
    status === "done"    ? "Scrape started ✓" :
    status === "error"   ? "Failed ✗" :
    "Run scrape now";

  return (
    <button
      onClick={handleClick}
      disabled={status === "running"}
      className={`px-3 py-1.5 text-sm rounded border transition-colors disabled:opacity-50 ${
        status === "done"  ? "border-green-600 text-green-400" :
        status === "error" ? "border-red-600 text-red-400" :
        "border-gray-600 text-gray-300 hover:border-gray-400"
      }`}
    >
      {label}
    </button>
  );
}
