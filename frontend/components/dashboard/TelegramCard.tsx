"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ChevronDown, Send } from "lucide-react";
import { useState } from "react";

import { getTelegramLinkStatus, unlinkTelegram } from "@/lib/api/telegram";
import { describeError } from "@/lib/errors";
import { formatDateTimeSP } from "@/lib/format";
import { useToast } from "@/lib/toast";
import { TelegramConnectFlow } from "@/components/dashboard/TelegramConnectFlow";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";

/**
 * Widget da Visão geral: mostra o link do Telegram direto na tela em vez de
 * exigir o script de terminal (scripts/gerar_link_telegram.py) — o vínculo
 * já é 100% self-service pela API, isto só dá uma UI a ele.
 *
 * Enquanto não há vínculo, o fluxo de conexão precisa de espaço (política,
 * QR code) e é o conteúdo principal da tela, então ganha um card cheio. Uma
 * vez conectado, vira só uma barra retrátil — o card cheio tomaria metade da
 * grade de gráficos por uma informação que, no dia a dia, é só um status.
 */
export function TelegramCard() {
  const queryClient = useQueryClient();
  const { show } = useToast();
  const [expanded, setExpanded] = useState(false);

  const statusQuery = useQuery({
    queryKey: ["telegram", "status"],
    queryFn: getTelegramLinkStatus,
  });

  const unlinkMutation = useMutation({
    mutationFn: unlinkTelegram,
    onSuccess: () => {
      show({ variant: "success", title: "Telegram desvinculado" });
      queryClient.invalidateQueries({ queryKey: ["telegram", "status"] });
    },
    onError: (error: unknown) => {
      show({
        variant: "error",
        title: "Não foi possível desvincular",
        description: describeError(error).message,
      });
    },
  });

  if (statusQuery.isLoading) {
    return (
      <section className="rounded-xl border border-border bg-surface p-5">
        <div className="space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </section>
    );
  }

  if (statusQuery.isError || !statusQuery.data) {
    return (
      <section className="rounded-xl border border-border bg-surface p-5">
        <ErrorState
          title="Não foi possível carregar o status do Telegram"
          onRetry={() => statusQuery.refetch()}
        />
      </section>
    );
  }

  const status = statusQuery.data;

  if (!status.linked) {
    return (
      <section className="rounded-xl border border-border bg-surface p-5">
        <header className="mb-4 flex items-center gap-2">
          <Send className="h-5 w-5 text-primary" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-surface-foreground">Telegram</h2>
        </header>
        <TelegramConnectFlow />
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-border bg-surface">
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        aria-expanded={expanded}
        className="flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left"
      >
        <span className="flex items-center gap-2">
          <Send className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="text-sm font-medium text-surface-foreground">Telegram</span>
          <span className="flex items-center gap-1 text-xs font-medium text-success">
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
            Conectado
          </span>
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-muted transition-transform ${expanded ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>
      {expanded ? (
        <div className="space-y-3 border-t border-border px-4 py-3">
          {status.linked_at ? (
            <p className="text-sm text-muted">Desde {formatDateTimeSP(status.linked_at)}</p>
          ) : null}
          <p className="text-sm text-muted">
            Registre receitas e despesas por texto ou áudio, e consulte o saldo direto na conversa com{" "}
            <code className="rounded bg-background px-1 py-0.5">/saldo</code>.
          </p>
          <Button variant="secondary" onClick={() => unlinkMutation.mutate()} loading={unlinkMutation.isPending}>
            Desvincular
          </Button>
        </div>
      ) : null}
    </section>
  );
}
