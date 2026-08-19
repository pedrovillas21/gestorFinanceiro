import { NextRequest, NextResponse } from "next/server";

import { relayError } from "@/lib/server/relay";
import { upstreamFetch } from "@/lib/server/upstream";
import { writeSession } from "@/lib/session/cookies";
import type { TokenResponse } from "@/lib/types";

/**
 * POST /api/auth/login — grava o par de tokens em cookie httpOnly e devolve
 * ao browser só o `user`. O TokenResponse nunca sai daqui: é o que faz o BFF
 * valer a pena (ver plan/Plano de Implementacao do Front-end - Dashboard
 * Next.js.md).
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.text();
  const upstream = await upstreamFetch("/auth/login", {
    method: "POST",
    body,
    headers: { "Content-Type": "application/json" },
    userAgent: request.headers.get("user-agent"),
  });

  if (!upstream.ok) {
    // Inclui o 429 do bloqueio progressivo — o Retry-After precisa chegar ao
    // browser para a contagem regressiva da tela de login.
    return relayError(upstream);
  }

  const tokens = (await upstream.json()) as TokenResponse;
  await writeSession(tokens);
  return NextResponse.json({ user: tokens.user });
}
