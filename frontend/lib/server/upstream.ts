// Único ponto do projeto que conhece a URL do FastAPI. `API_URL` é
// server-only (sem NEXT_PUBLIC_): o browser nunca fala diretamente com a API,
// só com o BFF (ver app/api/bff e app/api/auth).
const API_URL = process.env.API_URL ?? "http://localhost:8000";

export interface UpstreamRequestInit extends Omit<RequestInit, "headers"> {
  headers?: HeadersInit;
  accessToken?: string | null;
  /** Repassado ao back-end, que o grava como rótulo do dispositivo (truncado em 255). */
  userAgent?: string | null;
}

function buildHeaders(init: UpstreamRequestInit): Headers {
  const headers = new Headers(init.headers);
  if (init.accessToken) {
    headers.set("Authorization", `Bearer ${init.accessToken}`);
  }
  if (init.userAgent) {
    headers.set("User-Agent", init.userAgent);
  }
  return headers;
}

/** Chama uma rota sob /api/v1 do FastAPI. */
export function upstreamFetch(path: string, init: UpstreamRequestInit = {}): Promise<Response> {
  // Excesso de propriedades (accessToken, userAgent) não passa pelo spread:
  // TypeScript só checa "excess properties" em literais escritos na mão.
  return fetch(`${API_URL}/api/v1${path}`, {
    ...init,
    headers: buildHeaders(init),
    cache: "no-store",
  });
}

/** GET /health está montado na raiz do FastAPI, fora de /api/v1 — única rota nessa condição. */
export function upstreamHealthFetch(): Promise<Response> {
  return fetch(`${API_URL}/health`, { cache: "no-store" });
}

export { API_URL };
