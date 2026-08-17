import { NextRequest, NextResponse } from "next/server";

import { relayError } from "@/lib/server/relay";
import { upstreamFetch } from "@/lib/server/upstream";
import { clearSession, readSession } from "@/lib/session/cookies";

function unauthorized(): NextResponse {
  return NextResponse.json({ detail: "Credenciais inválidas" }, { status: 401 });
}

/** GET /api/auth/me — só necessário no boot frio (app sobe sem saber de quem é o cookie). */
export async function GET(): Promise<NextResponse> {
  const session = await readSession();
  if (!session?.accessToken) {
    return unauthorized();
  }
  const upstream = await upstreamFetch("/auth/me", { accessToken: session.accessToken });
  if (!upstream.ok) {
    return relayError(upstream);
  }
  return NextResponse.json(await upstream.json());
}

/** PATCH /api/auth/me — só `full_name`; nome em branco vira `null` no back-end. */
export async function PATCH(request: NextRequest): Promise<NextResponse> {
  const session = await readSession();
  if (!session?.accessToken) {
    return unauthorized();
  }
  const body = await request.text();
  const upstream = await upstreamFetch("/auth/me", {
    method: "PATCH",
    accessToken: session.accessToken,
    body,
    headers: { "Content-Type": "application/json" },
  });
  if (!upstream.ok) {
    return relayError(upstream);
  }
  return NextResponse.json(await upstream.json());
}

/** DELETE /api/auth/me — exclusão em cascata no back-end; a sessão local não sobrevive a isso. */
export async function DELETE(): Promise<NextResponse> {
  const session = await readSession();
  if (!session?.accessToken) {
    return unauthorized();
  }
  const upstream = await upstreamFetch("/auth/me", {
    method: "DELETE",
    accessToken: session.accessToken,
  });
  if (!upstream.ok) {
    return relayError(upstream);
  }
  await clearSession();
  return NextResponse.json(await upstream.json());
}
