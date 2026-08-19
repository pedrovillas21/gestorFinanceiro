import { NextResponse } from "next/server";

import { readSession } from "@/lib/session/cookies";

/**
 * GET /api/auth/session — checagem barata de "há sessão?" sem chamar o
 * back-end (ao contrário de GET /api/auth/me). Usada pelo guard do
 * `(dashboard)/layout.tsx` e por qualquer bootstrap client-side que precise
 * saber se há cookie antes de decidir buscar o perfil completo.
 */
export async function GET(): Promise<NextResponse> {
  const session = await readSession();
  return NextResponse.json({
    authenticated: session !== null,
    sessionId: session?.sessionId ?? null,
  });
}
