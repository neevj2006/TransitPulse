import { NextResponse } from "next/server";
import { publicEnv } from "@/lib/env";

export function GET() {
  return NextResponse.json({
    environment: publicEnv.NEXT_PUBLIC_APP_ENV,
    service: "transitpulse-web",
    status: "ok",
    version: publicEnv.NEXT_PUBLIC_APP_VERSION,
  });
}
