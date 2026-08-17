import axios, { type InternalAxiosRequestConfig } from "axios";

/**
 * Cliente HTTP do browser para o BFF, com single-flight de refresh embutido.
 *
 * O ponto mais crítico do projeto (07 §6 item 18, 05 §5.2): dois
 * `POST /auth/refresh` concorrentes com o mesmo refresh token caem na
 * detecção de reuso do back-end e derrubam TODAS as sessões do usuário. Não
 * há janela de graça — decisão fechada (08 §7).
 *
 * Duas camadas de serialização:
 * 1. `sharedRefresh` — promessa compartilhada no módulo, serializa dentro da
 *    aba. "Route Handlers cannot share data between requests" (doc do Next),
 *    então isso não pode viver no servidor.
 * 2. `navigator.locks` — serializa entre abas. Sem polyfill: onde não existe
 *    (SSR, ambiente de teste), cai para execução direta, ainda coberta pela
 *    camada 1 dentro da mesma aba.
 *
 * Double-checked locking: `gf_sess_epoch` (cookie não-httpOnly, só o
 * `expires_at` do access token) é relido depois de entrar na seção crítica.
 * Se mudou desde o 401 que disparou o refresh, outra aba já renovou — pula a
 * chamada e deixa a requisição original ser repetida com o cookie novo.
 */

const REFRESH_LOCK_NAME = "gf-auth-refresh";
const SESS_EPOCH_COOKIE = "gf_sess_epoch";

export class SessionExpiredError extends Error {
  constructor() {
    super("Sessão expirada. Faça login novamente.");
    this.name = "SessionExpiredError";
  }
}

function readSessEpoch(): string | null {
  if (typeof document === "undefined") {
    return null;
  }
  const match = document.cookie.match(new RegExp(`(?:^|; )${SESS_EPOCH_COOKIE}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

let sharedRefresh: Promise<void> | null = null;

async function attemptRefresh(observedEpoch: string | null): Promise<void> {
  const currentEpoch = readSessEpoch();
  if (currentEpoch !== null && currentEpoch !== observedEpoch) {
    // Outra aba já renovou entre o 401 observado e a entrada na seção crítica.
    return;
  }
  const response = await fetch("/api/auth/refresh", { method: "POST" });
  if (!response.ok) {
    // 401 no próprio refresh: o servidor já encerrou a sessão (reuso
    // detectado ou token vencido). Logout duro — não repetir nada.
    throw new SessionExpiredError();
  }
}

/**
 * `await`-a dentro de uma função explicitamente `Promise<void>` de propósito:
 * atribuir o retorno de `locks.request(...)` direto a uma variável confunde a
 * inferência de overload da tipagem do Web Locks (`Promise<Promise<void>>`).
 */
async function runExclusive(observedEpoch: string | null): Promise<void> {
  const locks = typeof navigator !== "undefined" ? navigator.locks : undefined;
  if (locks) {
    await locks.request(REFRESH_LOCK_NAME, () => attemptRefresh(observedEpoch));
  } else {
    await attemptRefresh(observedEpoch);
  }
}

/**
 * Garante uma sessão fresca, disparando no máximo um `POST /api/auth/refresh`
 * mesmo com N chamadores concorrentes. Exportado à parte do interceptor do
 * axios para ser testável sem precisar simular a camada de transporte HTTP.
 */
export async function ensureFreshSession(observedEpoch: string | null = readSessEpoch()): Promise<void> {
  if (!sharedRefresh) {
    sharedRefresh = runExclusive(observedEpoch).finally(() => {
      sharedRefresh = null;
    });
  }
  return sharedRefresh;
}

declare module "axios" {
  interface InternalAxiosRequestConfig {
    _retriedAfterRefresh?: boolean;
  }
}

export const http = axios.create({ baseURL: "/api/bff" });

http.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) {
      throw error;
    }
    const config = error.config as InternalAxiosRequestConfig | undefined;
    if (error.response?.status !== 401 || !config || config._retriedAfterRefresh) {
      throw error;
    }
    const observedEpoch = readSessEpoch();
    config._retriedAfterRefresh = true;
    await ensureFreshSession(observedEpoch);
    return http(config);
  },
);
