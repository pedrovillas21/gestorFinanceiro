"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, TrendingUp } from "lucide-react";
import Link from "next/link";

import { getPortfolio } from "@/lib/api/investments";
import { formatBRL } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";

/**
 * Bloco resumo da carteira na Visão geral (plan, Fase 4): valor de mercado,
 * custo investido e ganho não realizado, com atalho para Investimentos.
 * `GET /investments/portfolio` não é escopado por período — é o estado atual
 * da carteira — então este bloco não recebe `start`/`end`.
 *
 * Campos nulos são estado de negócio, não erro (resume/05 §6.3): quando
 * algum ativo com custódia está sem cotação, `total_market_value` e
 * `total_unrealized_gain` vêm `null` — nunca renderizar como R$ 0,00.
 */
export function PortfolioSummaryCard() {
  const portfolioQuery = useQuery({
    queryKey: ["investments", "portfolio"],
    queryFn: getPortfolio,
  });

  return (
    <section className="rounded-xl border border-border bg-surface p-5">
      <header className="mb-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-surface-foreground">Carteira de investimentos</h2>
        </div>
        <Link href="/investimentos" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
          Ver investimentos
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </header>

      {portfolioQuery.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ) : portfolioQuery.isError || !portfolioQuery.data ? (
        <ErrorState title="Não foi possível carregar a carteira" onRetry={() => portfolioQuery.refetch()} />
      ) : portfolioQuery.data.positions.length === 0 ? (
        <div className="space-y-3">
          <p className="text-sm text-muted">Nenhum investimento cadastrado ainda.</p>
          <Link href="/investimentos">
            <Button type="button" variant="secondary">
              Cadastrar ativo
            </Button>
          </Link>
        </div>
      ) : (
        <PortfolioTotals
          marketValue={portfolioQuery.data.total_market_value}
          investedCost={portfolioQuery.data.total_invested_cost}
          unrealizedGain={portfolioQuery.data.total_unrealized_gain}
        />
      )}
    </section>
  );
}

function PortfolioTotals({
  marketValue,
  investedCost,
  unrealizedGain,
}: {
  marketValue: string | null;
  investedCost: string;
  unrealizedGain: string | null;
}) {
  const partial = marketValue === null || unrealizedGain === null;
  const gainClass =
    unrealizedGain === null ? "text-muted" : unrealizedGain.startsWith("-") ? "text-danger" : "text-success";

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-xs text-muted">Valor de mercado</p>
          <p className="mt-0.5 font-medium tabular-nums text-surface-foreground">
            {marketValue !== null ? formatBRL(marketValue) : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted">Custo investido</p>
          <p className="mt-0.5 font-medium tabular-nums text-surface-foreground">{formatBRL(investedCost)}</p>
        </div>
        <div>
          <p className="text-xs text-muted">Ganho não realizado</p>
          <p className={`mt-0.5 font-medium tabular-nums ${gainClass}`}>
            {unrealizedGain !== null ? formatBRL(unrealizedGain, { signed: true }) : "—"}
          </p>
        </div>
      </div>
      {partial ? (
        <p className="text-xs text-warning">Carteira parcial — atualize as cotações para ver os valores completos.</p>
      ) : null}
    </div>
  );
}
