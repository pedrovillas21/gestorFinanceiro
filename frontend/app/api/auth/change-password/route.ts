import { NextRequest, NextResponse } from "next/server";

import { relayError } from "@/lib/server/relay";
import { upstreamFetch } from "@/lib/server/upstream";
import { readSession, writeSession } from "@/lib/session/cookies";
import type { TokenResponse } from "@/lib/types";

/**
 * POST /api/auth/change-password — devolve sempre um par de tokens novo (a
 * própria sessão que trocou a senha é substituída, mesmo com
 * `revoke_other_sessions: false`), então regravamos o cookie aqui também.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const session = await readSession();
  if (!session?.accessToken) {
    return NextResponse.json({ detail: "Credenciais inválidas" }, { status: 401 });
  }

  const body = await request.text();
  const upstream = await upstreamFetch("/auth/change-password", {
    method: "POST",
    accessToken: session.accessToken,
    body,
    headers: { "Content-Type": "application/json" },
    userAgent: request.headers.get("user-agent"),
  });

  if (!upstream.ok) {
    return relayError(upstream);
  }

  const tokens = (await upstream.json()) as TokenResponse;
  await writeSession(tokens);
  return NextResponse.json({ user: tokens.user });
}
