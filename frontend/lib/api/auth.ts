import axios from "axios";

import { ensureFreshSession } from "@/lib/api/http";
import { isAxiosLikeError } from "@/lib/errors";
import type { MessageResponse, UserResponse } from "@/lib/types";

/**
 * Cliente para as rotas dedicadas de auth (`app/api/auth/*`) — nunca o
 * catch-all `/api/bff`, que as recusa de propósito (ver plan, "Como o BFF
 * funciona"). Instância à parte de `lib/api/http.ts` porque login/registro
 * não têm sessão ainda para o interceptor de refresh renovar.
 */
const authHttp = axios.create({ baseURL: "/api/auth" });

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

export interface AuthResult {
  user: UserResponse;
}

export async function login(payload: LoginPayload): Promise<AuthResult> {
  const { data } = await authHttp.post<AuthResult>("/login", payload);
  return data;
}

export async function register(payload: RegisterPayload): Promise<AuthResult> {
  const { data } = await authHttp.post<AuthResult>("/register", payload);
  return data;
}

export async function logout(options: { allDevices?: boolean } = {}): Promise<MessageResponse> {
  const { data } = await authHttp.post<MessageResponse>("/logout", {
    all_devices: options.allDevices ?? false,
  });
  return data;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
  revoke_other_sessions?: boolean;
}

/**
 * POST /api/auth/change-password — o próprio Route Handler já regrava o
 * cookie de sessão com o par novo de tokens (troca de senha invalida os
 * antigos). Devolve o `user` atualizado, com `must_change_password` zerado.
 */
export async function changePassword(payload: ChangePasswordPayload): Promise<AuthResult> {
  const { data } = await authHttp.post<AuthResult>("/change-password", payload);
  return data;
}

/**
 * GET /api/auth/me com um retry único protegido pelo single-flight de
 * `ensureFreshSession` — o mesmo caminho crítico usado pelo cliente do BFF
 * (lib/api/http.ts), reaproveitado em vez de duplicado: um 401 aqui não pode
 * disparar um segundo `POST /auth/refresh` concorrente com o das telas do
 * dashboard.
 */
export async function fetchCurrentUser(): Promise<UserResponse> {
  try {
    const { data } = await authHttp.get<UserResponse>("/me");
    return data;
  } catch (error) {
    if (isAxiosLikeError(error) && error.response?.status === 401) {
      await ensureFreshSession();
      const { data } = await authHttp.get<UserResponse>("/me");
      return data;
    }
    throw error;
  }
}

export function isUnauthorized(error: unknown): boolean {
  return isAxiosLikeError(error) && error.response?.status === 401;
}

export function isConflict(error: unknown): boolean {
  return isAxiosLikeError(error) && error.response?.status === 409;
}

/** 429 do bloqueio progressivo de login — segundos até a próxima tentativa liberar. */
export function readRetryAfterSeconds(error: unknown): number | null {
  if (!axios.isAxiosError(error) || error.response?.status !== 429) {
    return null;
  }
  const header = error.response.headers?.["retry-after"];
  const seconds = Number(header);
  return Number.isFinite(seconds) && seconds > 0 ? seconds : null;
}
