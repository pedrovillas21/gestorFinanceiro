import { NextRequest, NextResponse } from "next/server";

import { relayError } from "@/lib/server/relay";
import { upstreamFetch } from "@/lib/server/upstream";
import { clearSession, readSession } from "@/lib/session/cookies";
import type { MessageResponse } from "@/lib/types";

async function readAllDevicesFlag(request: NextRequest): Promise<boolean> {
  const text = await request.text();
  if (!text) {
    return false;
  }
  try {
    const parsed = JSON.parse(text) as { all_devices?: unknown };
    return parsed.all_devices === true;
  } catch {
    return false;
  }
}

/**
 * POST /api/auth/logout — sempre chama o back-end antes de limpar o cookie:
 * descartar só no cliente deixa a sessão viva por até 30 dias no servidor.
 *
 * `{all_devices: true}` exige access token válido (o back-end devolve 401 sem
 * ele); sessão única é revogada pela posse do refresh token, sem exigir
 * token de acesso. Sem sessão local nenhuma, não há o que revogar — só
 * confirma o logout.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const allDevices = await readAllDevicesFlag(request);
  const session = await readSession();

  if (!session) {
    return NextResponse.json({ message: "Sessão já encerrada" } satisfies MessageResponse);
  }

  const upstream = await upstreamFetch("/auth/logout", {
    method: "POST",
    accessToken: allDevices ? session.accessToken : undefined,
    body: JSON.stringify(
      allDevices ? { all_devices: true } : { refresh_token: session.refreshToken },
    ),
    headers: { "Content-Type": "application/json" },
  });

  // Limpa o cookie local nos dois casos: em sucesso, a sessão foi revogada no
  // servidor; num 401 de `all_devices` sem access token válido, o cookie
  // local já não tem garantia nenhuma do próprio servidor — não faz sentido
  // mantê-lo só porque o pedido de derrubar tudo falhou.
  await clearSession();

  if (!upstream.ok) {
    return relayError(upstream);
  }

  return NextResponse.json((await upstream.json()) as MessageResponse);
}
