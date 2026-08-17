import { NextRequest, NextResponse } from "next/server";

import { relayError } from "@/lib/server/relay";
import { upstreamFetch } from "@/lib/server/upstream";
import { clearSession, readSession, writeSession } from "@/lib/session/cookies";
import type { TokenResponse } from "@/lib/types";

/**
 * POST /api/auth/refresh — chamada pelo single-flight de lib/api/http.ts, sem
 * corpo: o refresh token vem do cookie httpOnly, nunca do browser. Rota
 * pública no FastAPI, mas aqui já parte de uma sessão existente — sem cookie,
 * não há o que renovar.
 *
 * Um 401 aqui é logout duro (reuso detectado ou token vencido): o servidor já
 * encerrou a sessão, então o cookie local também precisa cair.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const session = await readSession();
  if (!session) {
    return NextResponse.json({ detail: "Nenhuma sessão para renovar" }, { status: 401 });
  }

  const upstream = await upstreamFetch("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: session.refreshToken }),
    headers: { "Content-Type": "application/json" },
    userAgent: request.headers.get("user-agent"),
  });

  if (!upstream.ok) {
    await clearSession();
    return relayError(upstream);
  }

  const tokens = (await upstream.json()) as TokenResponse;
  await writeSession(tokens);
  return NextResponse.json({ user: tokens.user });
}
