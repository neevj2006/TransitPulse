import { demoResponse } from "@/lib/demo";
import { isDemo } from "@/lib/env";

export function GET(request: Request) {
  if (!isDemo)
    return Response.json(
      { message: "Configure the public backend origin for live data." },
      { status: 503 },
    );
  const result = demoResponse(new URL(request.url));
  return Response.json(result.body, {
    status: result.status,
    headers: {
      "Cache-Control": "no-store",
      "X-TransitPulse-Mode": "demonstration",
    },
  });
}
