"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Send } from "lucide-react";

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
 */
export function TelegramCard() {
  const queryClient = useQueryClient();
  const { show } = useToast();

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

  function renderBody() {
    if (statusQuery.isLoading) {
      return (
        <div className="space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      );
    }
    if (statusQuery.isError || !statusQuery.data) {
      return (
        <ErrorState
          title="Não foi possível carregar o status do Telegram"
          onRetry={() => statusQuery.refetch()}
        />
      );
    }
    const status = statusQuery.data;
    if (!status.linked) {
      return <TelegramConnectFlow />;
    }
    return (
      <div className="space-y-3">
        <p className="flex items-center gap-2 text-sm font-medium text-success">
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
          Conectado
        </p>
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
    );
  }

  return (
    <section className="rounded-xl border border-border bg-surface p-5">
      <header className="mb-4 flex items-center gap-2">
        <Send className="h-5 w-5 text-primary" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-surface-foreground">Telegram</h2>
      </header>
      {renderBody()}
    </section>
  );
}
