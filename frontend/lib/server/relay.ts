import { NextResponse } from "next/server";

/**
 * Repassa uma resposta de erro do FastAPI ao browser, preservando o corpo
 * (`detail`, polimórfico — ver lib/errors.ts) e o `Retry-After` (429 do
 * login). Usado só pelas rotas dedicadas de auth: o catch-all (app/api/bff)
 * tem seu próprio repasse, mais amplo, porque também precisa streamar sucesso.
 */
export async function relayError(upstream: Response): Promise<NextResponse> {
  const body = await upstream.text();
  const headers = new Headers();
  const retryAfter = upstream.headers.get("Retry-After");
  if (retryAfter) {
    headers.set("Retry-After", retryAfter);
  }
  const contentType = upstream.headers.get("Content-Type");
  if (contentType) {
    headers.set("Content-Type", contentType);
  }
  return new NextResponse(body, { status: upstream.status, headers });
}
