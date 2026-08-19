import { cookies } from "next/headers";

import type { TokenResponse } from "@/lib/types";

// Só usado dentro de Route Handlers (app/api/auth/*, app/api/bff/*) — nunca
// importar este módulo de um Client Component.

const ACCESS_TOKEN_COOKIE = "gf_access_token";
const REFRESH_TOKEN_COOKIE = "gf_refresh_token";
const SESSION_ID_COOKIE = "gf_session_id";
/**
 * Não-httpOnly de propósito: o browser precisa ler este valor para o
 * double-checked locking do single-flight de refresh (lib/api/http.ts). Não é
 * segredo — carrega só o `expires_at` do access token, para o cliente notar
 * quando outra aba já renovou a sessão.
 */
const SESS_EPOCH_COOKIE = "gf_sess_epoch";

export const SESS_EPOCH_COOKIE_NAME = SESS_EPOCH_COOKIE;

export interface StoredSession {
  /** Pode ser string vazia se o cookie do access token expirou antes do refresh token. */
  accessToken: string;
  refreshToken: string;
  sessionId: string;
}

function secondsUntil(isoDate: string): number {
  const diffMs = new Date(isoDate).getTime() - Date.now();
  // Mínimo de 1s: um valor <= 0 faria o cookie nascer já expirado.
  return Math.max(1, Math.floor(diffMs / 1000));
}

function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

function httpOnlyOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    secure: isProduction(),
    sameSite: "lax" as const,
    path: "/",
    maxAge: maxAgeSeconds,
  };
}

function epochCookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: false,
    secure: isProduction(),
    sameSite: "lax" as const,
    path: "/",
    maxAge: maxAgeSeconds,
  };
}

/**
 * Grava os três valores do TokenResponse (access, refresh, session_id) mais o
 * `sess_epoch`. Os três primeiros compartilham o prazo do refresh token: o
 * access token dura só 30 minutos por conteúdo (JWT), mas o cookie precisa
 * sobreviver até a próxima renovação poder acontecer — senão o BFF perde a
 * sessão inteira 30 minutos depois do login, mesmo com o refresh token ainda
 * válido por dias.
 */
export async function writeSession(tokens: TokenResponse): Promise<void> {
  const store = await cookies();
  const refreshMaxAge = secondsUntil(tokens.refresh_expires_at);

  store.set(ACCESS_TOKEN_COOKIE, tokens.access_token, httpOnlyOptions(refreshMaxAge));
  store.set(REFRESH_TOKEN_COOKIE, tokens.refresh_token, httpOnlyOptions(refreshMaxAge));
  store.set(SESSION_ID_COOKIE, tokens.session_id, httpOnlyOptions(refreshMaxAge));
  store.set(SESS_EPOCH_COOKIE, tokens.expires_at, epochCookieOptions(refreshMaxAge));
}

/** `null` quando não há refresh token — sem ele não há sessão para renovar nem para revogar. */
export async function readSession(): Promise<StoredSession | null> {
  const store = await cookies();
  const refreshToken = store.get(REFRESH_TOKEN_COOKIE)?.value;
  if (!refreshToken) {
    return null;
  }
  return {
    accessToken: store.get(ACCESS_TOKEN_COOKIE)?.value ?? "",
    refreshToken,
    sessionId: store.get(SESSION_ID_COOKIE)?.value ?? "",
  };
}

export async function clearSession(): Promise<void> {
  const store = await cookies();
  store.delete(ACCESS_TOKEN_COOKIE);
  store.delete(REFRESH_TOKEN_COOKIE);
  store.delete(SESSION_ID_COOKIE);
  store.delete(SESS_EPOCH_COOKIE);
}
