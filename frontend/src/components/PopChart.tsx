// frontend/src/components/PopChart.tsx
"use client";

interface Props {
  population: number;
}

export default function PopChart({ population }: Props) {
  return (
    <div className="rounded-lg border border-white/10 p-4"
         style={{ background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)" }}>
      <div className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-3">
        PSA 10 Population
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold text-gray-100 tabular-nums">
          {population.toLocaleString()}
        </span>
        <span className="text-sm text-gray-500">copies graded PSA 10</span>
      </div>
    </div>
  );
}
