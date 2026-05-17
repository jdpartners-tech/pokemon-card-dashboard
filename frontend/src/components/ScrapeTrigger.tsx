"use client";

import { useState } from "react";
import { triggerScrape, triggerBackfill, triggerSnkrdunkBackfill } from "@/lib/api";

type Status = "idle" | "running" | "done" | "error" | "disabled";

function AdminButton({
  onAction,
  labels,
}: {
  onAction: () => Promise<void>;
  labels: { idle: string; running: string; done: string; error: string };
}) {
  const [status, setStatus] = useState<Status>("idle");

  async function handleClick() {
    if (status === "running" || status === "disabled") return;
    setStatus("running");
    try {
      await onAction();
      setStatus("done");
      setTimeout(() => setStatus("idle"), 3000);
    } catch (err: unknown) {
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
        Disabled
      </span>
    );
  }

  const label =
    status === "running" ? labels.running :
    status === "done"    ? labels.done :
    status === "error"   ? labels.error :
    labels.idle;

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

export default function ScrapeTrigger() {
  return (
    <div className="flex gap-2">
      <AdminButton
        onAction={triggerScrape}
        labels={{ idle: "Run scrape now", running: "Starting…", done: "Scrape started ✓", error: "Failed ✗" }}
      />
      <AdminButton
        onAction={triggerBackfill}
        labels={{ idle: "Backfill PC history", running: "Starting…", done: "Backfill started ✓", error: "Failed ✗" }}
      />
      <AdminButton
        onAction={triggerSnkrdunkBackfill}
        labels={{ idle: "Backfill Snkrdunk", running: "Starting…", done: "Backfill started ✓", error: "Failed ✗" }}
      />
    </div>
  );
}
