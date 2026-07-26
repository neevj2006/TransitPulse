import { z } from "zod";

const publicEnvSchema = z.object({
  NEXT_PUBLIC_APP_ENV: z
    .enum(["development", "preview", "production"])
    .default("development"),
  NEXT_PUBLIC_APP_VERSION: z.string().min(1).default("0.1.0"),
  NEXT_PUBLIC_API_BASE_URL: z.string().url().optional(),
  NEXT_PUBLIC_MAP_STYLE_LIGHT_URL: z
    .string()
    .url()
    .default("https://tiles.openfreemap.org/styles/liberty"),
  NEXT_PUBLIC_MAP_STYLE_DARK_URL: z
    .string()
    .url()
    .default("https://tiles.openfreemap.org/styles/dark"),
});

export const publicEnv = publicEnvSchema.parse({
  NEXT_PUBLIC_APP_ENV: process.env.NEXT_PUBLIC_APP_ENV,
  NEXT_PUBLIC_APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION,
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_MAP_STYLE_LIGHT_URL: process.env.NEXT_PUBLIC_MAP_STYLE_LIGHT_URL,
  NEXT_PUBLIC_MAP_STYLE_DARK_URL: process.env.NEXT_PUBLIC_MAP_STYLE_DARK_URL,
});
