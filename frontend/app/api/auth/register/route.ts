import { NextRequest, NextResponse } from "next/server";

import { relayError } from "@/lib/server/relay";
import { upstreamFetch } from "@/lib/server/upstream";
import { writeSession } from "@/lib/session/cookies";
import type { TokenResponse } from "@/lib/types";

/** POST /api/auth/register — mesma lógica do login: grava cookie, devolve só o `user`. */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.text();
  const upstream = await upstreamFetch("/auth/register", {
    method: "POST",
    body,
    headers: { "Content-Type": "application/json" },
    userAgent: request.headers.get("user-agent"),
  });

  if (!upstream.ok) {
    return relayError(upstream);
  }

  const tokens = (await upstream.json()) as TokenResponse;
  await writeSession(tokens);
  return NextResponse.json({ user: tokens.user }, { status: 201 });
}
