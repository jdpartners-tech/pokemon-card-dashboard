"use client";

import { useEffect, useState } from "react";

interface Props {
  name: string;
  cardNumber?: string | null;
}

export default function CardThumb({ name, cardNumber }: Props) {
  const [imgUrl, setImgUrl] = useState<string | null>(null);

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
        setImgUrl(card?.images?.small ?? null);
      })
      .catch(() => null);
  }, [name, cardNumber]);

  if (!imgUrl) {
    return (
      <div className="w-8 h-11 rounded bg-gray-800 flex-shrink-0" />
    );
  }

  return (
    <img
      src={imgUrl}
      alt={name}
      className="w-8 h-11 object-contain rounded flex-shrink-0"
    />
  );
}
