import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "TransitPulse",
    short_name: "TransitPulse",
    description: "Real-time public-transit reliability and connection risk.",
    start_url: "/",
    display: "standalone",
    background_color: "#F5F7FA",
    theme_color: "#1859C9",
    icons: [
      { src: "/icon", sizes: "512x512", type: "image/png", purpose: "any" },
      {
        src: "/icon",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
