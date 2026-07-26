import { z } from "zod";
import { publicEnv } from "@/lib/env";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const base = publicEnv.NEXT_PUBLIC_API_BASE_URL ?? "";
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  if (!response.ok)
    throw new ApiError(response.status, `Request failed (${response.status})`);
  return schema.parse(await response.json());
}
