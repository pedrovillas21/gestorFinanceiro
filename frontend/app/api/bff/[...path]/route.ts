import { NextRequest, NextResponse } from "next/server";

import { API_URL } from "@/lib/server/upstream";
import { readSession } from "@/lib/session/cookies";

/**
 * Só estas rotas de auth têm handler dedicado (app/api/auth/*). Deixá-las
 * passar por aqui devolveria o TokenResponse inteiro ao browser — vazando
 * access_token e refresh_token, o buraco que o BFF existe para fechar.
 *
 * `auth/sessions` (plural, GET /auth/sessions) NÃO entra nesta lista: não tem
 * rota dedicada e a resposta não carrega segredo nenhum.
 */
const BLOCKED_AUTH_SUBPATHS = new Set([
  "auth/login",
  "auth/register",
  "auth/refresh",
  "auth/logout",
  "auth/change-password",
  "auth/me",
]);

// Cabeçalhos de resposta que o browser precisa enxergar. O backend não
// declara expose_headers no CORS, então sem o BFF esses dois ficavam
// invisíveis para o fetch/axios do browser em requisições cross-origin;
// mesma origem não tem essa restrição, mas repassamos do mesmo jeito.
const FORWARDED_RESPONSE_HEADERS = ["content-type", "content-disposition", "retry-after"];

type RouteContext = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const { path } = await context.params;
  const joined = path.join("/");

  if (BLOCKED_AUTH_SUBPATHS.has(joined)) {
    return NextResponse.json({ detail: "Use a rota dedicada de autenticação" }, { status: 404 });
  }

  const session = await readSession();

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("cookie"); // O cookie é do Next, não deve seguir para o FastAPI.
  headers.delete("content-length"); // Recalculado pelo fetch ao streamar o body.
  if (session?.accessToken) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  } else {
    headers.delete("authorization");
  }

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const upstreamUrl = `${API_URL}/api/v1/${joined}${request.nextUrl.search}`;

  const upstream = await fetch(upstreamUrl, {
    method: request.method,
    headers,
    // Streama o corpo (multipart de importação, JSON) sem bufferizar em memória.
    body: hasBody ? request.body : undefined,
    // Exigido pelo Node/undici quando o body é um ReadableStream. Ainda não
    // está no tipo RequestInit do lib.dom incluso neste projeto.
    // @ts-expect-error -- duplex não está tipado em lib.dom.d.ts ainda
    duplex: hasBody ? "half" : undefined,
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) {
      responseHeaders.set(name, value);
    }
  }

  // Streama a resposta de volta (blobs de exportação, listas grandes) sem bufferizar.
  return new NextResponse(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return handle(request, context);
}
export async function POST(request: NextRequest, context: RouteContext) {
  return handle(request, context);
}
export async function PATCH(request: NextRequest, context: RouteContext) {
  return handle(request, context);
}
export async function DELETE(request: NextRequest, context: RouteContext) {
  return handle(request, context);
}
