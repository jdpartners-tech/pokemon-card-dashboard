import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "PokéInvest",
    short_name: "PokéInvest",
    description: "PSA 10 Pokémon card investment tracker",
    start_url: "/",
    display: "standalone",
    background_color: "#06090e",
    theme_color: "#0f172a",
    icons: [
      { src: "/icon", sizes: "32x32", type: "image/png" },
      { src: "/apple-icon", sizes: "180x180", type: "image/png" },
    ],
  };
}
