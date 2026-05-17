"use client";
import { useState } from "react";

type ButtonState = "idle" | "loading" | "done" | "error";

function AdminButton({ label, endpoint }: { label: string; endpoint: string }) {
  const [state, setState] = useState<ButtonState>("idle");

  async function handle() {
    setState("loading");
    try {
      const r = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}${endpoint}`,
        { method: "POST" }
      );
      setState(r.ok ? "done" : "error");
    } catch {
      setState("error");
    }
    setTimeout(() => setState("idle"), 4000);
  }

  const labels: Record<ButtonState, string> = {
    idle: label, loading: "Starting…", done: "Started ✓", error: "Error ✗",
  };

  return (
    <button
      onClick={handle}
      disabled={state === "loading"}
      className={`px-3 py-1.5 text-xs rounded border transition-colors disabled:opacity-50 ${
        state === "done" ? "border-green-600 text-green-400" :
        state === "error" ? "border-red-600 text-red-400" :
        "border-gray-600 text-gray-400 hover:border-gray-400"
      }`}
    >
      {labels[state]}
    </button>
  );
}

export default function ScrapeTrigger() {
  return (
    <div className="flex gap-2 flex-wrap">
      <AdminButton label="Scrape now" endpoint="/admin/scrape" />
      <AdminButton label="Backfill history" endpoint="/admin/backfill" />
      <AdminButton label="Backfill Snkrdunk" endpoint="/admin/backfill/snkrdunk" />
    </div>
  );
}
