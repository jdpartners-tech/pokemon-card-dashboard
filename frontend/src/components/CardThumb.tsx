"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  name: string;
  cardNumber?: string | null;
}

export default function CardThumb({ name, cardNumber }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [imgUrl, setImgUrl] = useState<string | null>(null);

  // Only start fetching once the row is near the viewport
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { rootMargin: "300px" }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (!visible) return;
    const query = cardNumber
      ? `name:"${name}" number:${cardNumber.split("/")[0]}`
      : `name:"${name}"`;

    fetch(
      `https://api.pokemontcg.io/v2/cards?q=${encodeURIComponent(query)}&pageSize=1`,
      { headers: { Accept: "application/json" } }
    )
      .then((r) => r.json())
      .then((data) => {
        const card = data?.data?.[0];
        setImgUrl(card?.images?.small ?? null);
      })
      .catch(() => null);
  }, [visible, name, cardNumber]);

  return (
    <div ref={ref} className="w-8 h-11 flex-shrink-0">
      {imgUrl ? (
        <img src={imgUrl} alt={name} className="w-8 h-11 object-contain rounded" />
      ) : (
        <div className="w-8 h-11 rounded bg-gray-800" />
      )}
    </div>
  );
}
