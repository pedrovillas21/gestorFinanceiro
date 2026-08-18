import { http } from "@/lib/api/http";
import type {
  PrivacyPolicyResponse,
  TelegramLinkResponse,
  TelegramLinkStatus,
  TelegramUnlinkResponse,
} from "@/lib/types";

/**
 * `/telegram/*` passa pelo catch-all do BFF (`lib/api/http.ts`, baseURL
 * `/api/bff`) como qualquer outra rota de dado — só `/auth/*` tem rota
 * dedicada. Ordem exigida pelo back-end (resume/05 §Telegram): status →
 * política (se não vinculado) → gerar link com o consentimento.
 */

export async function getTelegramLinkStatus(): Promise<TelegramLinkStatus> {
  const { data } = await http.get<TelegramLinkStatus>("/telegram/link");
  return data;
}

export async function getTelegramPrivacyPolicy(): Promise<PrivacyPolicyResponse> {
  const { data } = await http.get<PrivacyPolicyResponse>("/telegram/privacy-policy");
  return data;
}

export interface CreateTelegramLinkPayload {
  consent: boolean;
  consent_version: string;
}

export async function createTelegramLink(
  payload: CreateTelegramLinkPayload,
): Promise<TelegramLinkResponse> {
  const { data } = await http.post<TelegramLinkResponse>("/telegram/link", payload);
  return data;
}

export async function unlinkTelegram(): Promise<TelegramUnlinkResponse> {
  const { data } = await http.delete<TelegramUnlinkResponse>("/telegram/link");
  return data;
}
