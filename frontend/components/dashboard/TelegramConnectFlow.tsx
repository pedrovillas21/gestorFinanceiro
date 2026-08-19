"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { ChevronDown, Send } from "lucide-react";
import { useEffect, useState } from "react";
import QRCode from "qrcode";

import { createTelegramLink, getTelegramPrivacyPolicy } from "@/lib/api/telegram";
import { describeError } from "@/lib/errors";
import type { TelegramLinkResponse } from "@/lib/types";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";

/** Segundos até `expiresAt`, recalculado a cada tick de um timer — nunca lido direto do render. */
function useCountdownSeconds(expiresAt: string | null): number | null {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!expiresAt) {
      return;
    }
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [expiresAt]);

  if (!expiresAt) {
    return null;
  }
  return Math.max(0, Math.round((new Date(expiresAt).getTime() - now) / 1000));
}

function formatCountdown(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}

/**
 * Fluxo de conexão, na ordem exigida pelo back-end (plan, Fase 8): política
 * de privacidade → consentimento versionado → `POST /telegram/link` → deep
 * link com contagem regressiva de 30 min. Renderizado só quando
 * `GET /telegram/link` diz que a conta ainda não está vinculada.
 */
export function TelegramConnectFlow() {
  const queryClient = useQueryClient();
  const policyQuery = useQuery({
    queryKey: ["telegram", "privacy-policy"],
    queryFn: getTelegramPrivacyPolicy,
  });

  const [policyOpen, setPolicyOpen] = useState(false);
  const [policyRead, setPolicyRead] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);
  const [link, setLink] = useState<TelegramLinkResponse | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  // Chave do link a que `qrDataUrl` pertence — usado para nunca renderizar o
  // QR do link anterior enquanto o novo ainda está sendo gerado (ver
  // `currentQrDataUrl` abaixo), sem precisar de um `setQrDataUrl(null)`
  // síncrono no corpo do efeito.
  const [qrGeneratedFor, setQrGeneratedFor] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const remainingSeconds = useCountdownSeconds(link?.expires_at ?? null);
  const expired = link !== null && remainingSeconds !== null && remainingSeconds <= 0;

  const linkMutation = useMutation({
    mutationFn: createTelegramLink,
    onSuccess: (data) => {
      setLink(data);
      setFormError(null);
    },
    onError: (error: unknown) => {
      const status = axios.isAxiosError(error) ? error.response?.status : undefined;
      if (status === 409) {
        // A política mudou com a tela aberta — recomeça o aceite do zero.
        setFormError("A política de privacidade mudou desde que você abriu esta tela. Leia de novo e confirme.");
        setPolicyOpen(false);
        setPolicyRead(false);
        setConsentChecked(false);
        queryClient.invalidateQueries({ queryKey: ["telegram", "privacy-policy"] });
        return;
      }
      if (status === 503) {
        setFormError("A política de privacidade ainda não está publicada. Tente novamente em instantes.");
        return;
      }
      setFormError(describeError(error).message);
    },
  });

  // Gera o QR a partir do deep link sempre que ele muda — canvas/data URL fica
  // só no cliente, sem SSR (o `qrcode` não roda no Edge Runtime do Next). Sem
  // link ainda, não há nada a fazer: o efeito só sincroniza com a lib
  // externa, nunca ajusta estado de forma síncrona no próprio corpo.
  useEffect(() => {
    if (!link) {
      return;
    }
    let cancelled = false;
    const deepLink = link.deep_link;
    QRCode.toDataURL(deepLink, { margin: 1, width: 220 })
      .then((url) => {
        if (!cancelled) {
          setQrDataUrl(url);
          setQrGeneratedFor(deepLink);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setQrDataUrl(null);
          setQrGeneratedFor(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [link]);

  // Só mostra o QR se ele pertence ao link atual — evita o quadro do link
  // anterior piscar enquanto o novo ainda está sendo gerado.
  const currentQrDataUrl = link && qrGeneratedFor === link.deep_link ? qrDataUrl : null;

  if (policyQuery.isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-9 w-full" />
      </div>
    );
  }

  if (policyQuery.isError || !policyQuery.data) {
    return (
      <ErrorState
        title="Não foi possível carregar a política de privacidade"
        onRetry={() => policyQuery.refetch()}
      />
    );
  }

  const policy = policyQuery.data;

  if (link && !expired) {
    return (
      <div className="space-y-3">
        {formError ? <Alert variant="error">{formError}</Alert> : null}
        <p className="text-sm text-muted">
          Abra no Telegram para concluir — o link expira em{" "}
          <span className="font-medium tabular-nums text-foreground">
            {formatCountdown(remainingSeconds ?? 0)}
          </span>
          .
        </p>
        <a
          href={link.deep_link}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
        >
          <Send className="h-4 w-4" aria-hidden="true" />
          Abrir no Telegram
        </a>
        {currentQrDataUrl ? (
          <div className="flex flex-col items-start gap-1">
            {/* eslint-disable-next-line @next/next/no-img-element -- data URL gerado no cliente, next/image não se aplica */}
            <img
              src={currentQrDataUrl}
              alt="QR code para abrir a conversa com o bot no Telegram"
              width={160}
              height={160}
              className="rounded-md border border-border"
            />
            <p className="text-xs text-muted">Ou aponte a câmera do celular para o QR code.</p>
          </div>
        ) : null}
        <Button
          variant="ghost"
          onClick={() => linkMutation.mutate({ consent: true, consent_version: policy.version })}
          loading={linkMutation.isPending}
        >
          Gerar novo link
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {formError ? <Alert variant="error">{formError}</Alert> : null}
      {expired ? <Alert variant="warning">O link anterior expirou. Gere um novo abaixo.</Alert> : null}
      <p className="text-sm text-muted">
        Registre receitas e despesas por texto ou áudio, e consulte o saldo direto na conversa com{" "}
        <code className="rounded bg-background px-1 py-0.5">/saldo</code>.
      </p>

      <div className="rounded-md border border-border">
        <button
          type="button"
          onClick={() => {
            setPolicyOpen((current) => !current);
            setPolicyRead(true);
          }}
          aria-expanded={policyOpen}
          className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium text-surface-foreground"
        >
          <span>Política de privacidade ({policy.version})</span>
          <ChevronDown
            className={`h-4 w-4 shrink-0 transition-transform ${policyOpen ? "rotate-180" : ""}`}
            aria-hidden="true"
          />
        </button>
        {policyOpen ? (
          <div className="max-h-48 overflow-y-auto whitespace-pre-wrap border-t border-border px-3 py-2 text-xs text-muted">
            {policy.content}
          </div>
        ) : null}
      </div>

      <label className="flex items-start gap-2 text-sm text-surface-foreground">
        <input
          type="checkbox"
          checked={consentChecked}
          disabled={!policyRead}
          onChange={(event) => setConsentChecked(event.target.checked)}
          className="mt-0.5"
        />
        <span>
          Li e aceito a política de privacidade (versão {policy.version}) para conectar o Telegram.
          {!policyRead ? (
            <span className="block text-xs text-muted">Abra a política acima antes de marcar.</span>
          ) : null}
        </span>
      </label>

      <Button
        disabled={!consentChecked}
        loading={linkMutation.isPending}
        onClick={() => linkMutation.mutate({ consent: true, consent_version: policy.version })}
      >
        Gerar link do Telegram
      </Button>
    </div>
  );
}
