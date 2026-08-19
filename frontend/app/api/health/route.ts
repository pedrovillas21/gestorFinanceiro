import { NextResponse } from "next/server";

import { upstreamHealthFetch } from "@/lib/server/upstream";

/** GET /api/health — repassa o único endpoint do FastAPI fora de /api/v1. */
export async function GET(): Promise<NextResponse> {
  try {
    const upstream = await upstreamHealthFetch();
    return NextResponse.json(await upstream.json(), { status: upstream.status });
  } catch {
    return NextResponse.json({ status: "unreachable" }, { status: 503 });
  }
}
