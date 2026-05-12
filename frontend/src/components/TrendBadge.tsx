interface Props {
  value: number;
}

export default function TrendBadge({ value }: Props) {
  const positive = value >= 0;
  return (
    <span
      className={`inline-block text-xs font-medium px-1.5 py-0.5 rounded ${
        positive ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"
      }`}
    >
      {positive ? "+" : ""}
      {value.toFixed(1)}%
    </span>
  );
}
