"use client";

import { useQuery } from "@tanstack/react-query";
import Decimal from "decimal.js";
import { LayoutDashboard, Plus, Receipt } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

import { getFinancialSummary, getFinancialTimeseries } from "@/lib/api/dashboard";
import { periodToSearchParams, readPeriodFromSearchParams } from "@/lib/period";
import { pickGranularity } from "@/lib/timeseries";
import type { TransactionType } from "@/lib/types";
import { CategoryChart } from "@/components/charts/CategoryChart";
import { EvolutionChart } from "@/components/charts/EvolutionChart";
import { CategoryTable } from "@/components/dashboard/CategoryTable";
import { PortfolioSummaryCard } from "@/components/dashboard/PortfolioSummaryCard";
import { TelegramCard } from "@/components/dashboard/TelegramCard";
import { KpiCards } from "@/components/dashboard/KpiCards";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";

const CATEGORY_TYPE_LABEL: Record<TransactionType, string> = {
  expense: "Despesas",
  income: "Receitas",
};

export default function OverviewPage() {
  // useSearchParams (o período vem da URL, lido pelo PeriodSelector global no
  // Topbar) exige um limite de Suspense em build estático — mesma nota de
  // components/layout/Topbar.tsx e app/(dashboard)/transacoes/page.tsx.
  return (
    <Suspense fallback={<PageSkeleton />}>
      <OverviewPageContent />
    </Suspense>
  );
}

function OverviewPageContent() {
  const searchParams = useSearchParams();
  const period = useMemo(
    () =>
      readPeriodFromSearchParams({
        period: searchParams.get("period"),
        start: searchParams.get("start"),
        end: searchParams.get("end"),
      }),
    [searchParams],
  );

  const [categoryType, setCategoryType] = useState<TransactionType>("expense");
  const granularity = useMemo(() => pickGranularity(period.start, period.end), [period.start, period.end]);

  const summaryQuery = useQuery({
    queryKey: ["dashboard", "summary", period.start, period.end, categoryType],
    queryFn: () => getFinancialSummary({ start: period.start, end: period.end, type: categoryType }),
  });

  const timeseriesQuery = useQuery({
    queryKey: ["dashboard", "timeseries", period.start, period.end, granularity],
    queryFn: () => getFinancialTimeseries({ start: period.start, end: period.end, granularity }),
  });

  const periodQuery = `?${new URLSearchParams(periodToSearchParams(period)).toString()}`;
  // Variável local em vez de `summaryQuery.data` repetido: o TypeScript só
  // estreita `| undefined` a partir do controle de fluxo sobre uma const,
  // não através do campo de um objeto reavaliado a cada acesso.
  const summary = summaryQuery.data;
  const isEmpty = summary ? new Decimal(summary.income).isZero() && new Decimal(summary.expense).isZero() : false;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Visão geral</h1>
        <p className="text-sm text-muted">
          Receitas, despesas e evolução do período selecionado no topo da tela.
        </p>
      </div>

      <TelegramCard />

      {summaryQuery.isError ? (
        <ErrorState title="Não foi possível carregar o resumo financeiro" onRetry={() => summaryQuery.refetch()} />
      ) : summaryQuery.isLoading || !summary ? (
        <ContentSkeleton />
      ) : isEmpty ? (
        <EmptyState
          icon={LayoutDashboard}
          title="Nenhuma transação neste período"
          description="Cadastre a primeira transação pela tela ou registre pelo Telegram para começar a ver KPIs e gráficos aqui."
          action={
            <Link href={`/transacoes${periodQuery}`}>
              <Button type="button">
                <Plus className="h-4 w-4" aria-hidden="true" />
                Nova transação
              </Button>
            </Link>
          }
        />
      ) : (
        <>
          <KpiCards income={summary.income} expense={summary.expense} balance={summary.balance} />

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-xl border border-border bg-surface p-5">
              <header className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-surface-foreground">
                  {CATEGORY_TYPE_LABEL[summary.by_category_type]} por categoria
                </h2>
                <div className="flex gap-1 rounded-md border border-border p-0.5">
                  {(["expense", "income"] as const).map((value) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setCategoryType(value)}
                      aria-pressed={categoryType === value}
                      className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                        categoryType === value
                          ? "bg-primary text-primary-foreground"
                          : "text-muted hover:text-surface-foreground"
                      }`}
                    >
                      {CATEGORY_TYPE_LABEL[value]}
                    </button>
                  ))}
                </div>
              </header>
              {summary.by_category.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted">
                  Sem {CATEGORY_TYPE_LABEL[summary.by_category_type].toLowerCase()} categorizadas neste período.
                </p>
              ) : (
                <CategoryChart categories={summary.by_category} type={summary.by_category_type} />
              )}
            </section>

            <section className="rounded-xl border border-border bg-surface p-5">
              <header className="mb-4">
                <h2 className="text-sm font-semibold text-surface-foreground">Evolução no período</h2>
              </header>
              {timeseriesQuery.isError ? (
                <ErrorState title="Não foi possível carregar a evolução" onRetry={() => timeseriesQuery.refetch()} />
              ) : timeseriesQuery.isLoading || !timeseriesQuery.data ? (
                <Skeleton className="h-72 w-full" />
              ) : (
                <EvolutionChart points={timeseriesQuery.data.points} granularity={timeseriesQuery.data.granularity} />
              )}
            </section>
          </div>

          {summary.by_category.length > 0 ? (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-surface-foreground">
                {CATEGORY_TYPE_LABEL[summary.by_category_type]} por categoria — detalhado
              </h2>
              <CategoryTable categories={summary.by_category} />
            </section>
          ) : null}

          <PortfolioSummaryCard />

          <div className="flex flex-wrap gap-2">
            <Link href={`/transacoes${periodQuery}`}>
              <Button type="button" variant="secondary">
                <Plus className="h-4 w-4" aria-hidden="true" />
                Nova transação
              </Button>
            </Link>
            <Link href={`/transacoes${periodQuery}`}>
              <Button type="button" variant="ghost">
                <Receipt className="h-4 w-4" aria-hidden="true" />
                Ver todas as transações
              </Button>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

function ContentSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-72 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-24 w-full" />
      <ContentSkeleton />
    </div>
  );
}
