import { z } from "zod";

const publicEnvSchema = z.object({
  NEXT_PUBLIC_APP_ENV: z
    .enum(["development", "preview", "production"])
    .default("development"),
  NEXT_PUBLIC_APP_VERSION: z.string().min(1).default("0.1.0"),
});

export const publicEnv = publicEnvSchema.parse({
  NEXT_PUBLIC_APP_ENV: process.env.NEXT_PUBLIC_APP_ENV,
  NEXT_PUBLIC_APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION,
});
