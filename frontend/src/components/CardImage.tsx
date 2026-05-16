"use client";

import { useEffect, useState } from "react";

interface Props {
  name: string;
  setName: string;
  cardNumber?: string | null;
}

export default function CardImage({ name, setName, cardNumber }: Props) {
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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
        setImgUrl(card?.images?.large ?? card?.images?.small ?? null);
      })
      .catch(() => setImgUrl(null))
      .finally(() => setLoading(false));
  }, [name, cardNumber]);

  if (loading) {
    return (
      <div className="w-48 h-64 rounded-lg bg-gray-800 animate-pulse" />
    );
  }

  if (!imgUrl) return null;

  return (
    <img
      src={imgUrl}
      alt={`${name} card`}
      className="w-48 rounded-lg shadow-lg shadow-black/50"
    />
  );
}
