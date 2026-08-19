"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus, Receipt } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

import { listTransactionCategories, listTransactions } from "@/lib/api/transactions";
import { PAGINATION } from "@/lib/api/pagination";
import { readPeriodFromSearchParams } from "@/lib/period";
import type { TransactionResponse } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { ExportButton } from "@/components/transactions/ExportButton";
import { TransactionFilters, type TransactionFiltersValue } from "@/components/transactions/TransactionFilters";
import { TransactionFormModal } from "@/components/transactions/TransactionFormModal";
import { TransactionsPagination } from "@/components/transactions/TransactionsPagination";
import { TransactionsTable, type SortState } from "@/components/transactions/TransactionsTable";

const LIMIT = PAGINATION.transactions.defaultLimit;

export default function TransactionsPage() {
  // useSearchParams (o período vem da URL, lido pelo PeriodSelector global no
  // Topbar) exige um limite de Suspense em build estático — mesma nota de
  // components/layout/Topbar.tsx.
  return (
    <Suspense fallback={<PageSkeleton />}>
      <TransactionsPageContent />
    </Suspense>
  );
}

function TransactionsPageContent() {
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

  const [filters, setFilters] = useState<TransactionFiltersValue>({ type: undefined, category: undefined, search: "" });
  const [sort, setSort] = useState<SortState>({ orderBy: "occurred_at", order: "desc" });
  const [offset, setOffset] = useState(0);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<TransactionResponse | null>(null);

  function updateFilters(next: TransactionFiltersValue) {
    setFilters(next);
    setOffset(0);
  }

  function updateSort(next: SortState) {
    setSort(next);
    setOffset(0);
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(transaction: TransactionResponse) {
    setEditing(transaction);
    setFormOpen(true);
  }

  const listParams = {
    start: period.start,
    end: period.end,
    type: filters.type,
    category: filters.category,
    search: filters.search || undefined,
    order_by: sort.orderBy,
    order: sort.order,
    limit: LIMIT,
    offset,
  };

  const transactionsQuery = useQuery({
    queryKey: ["transactions", "list", listParams],
    queryFn: () => listTransactions(listParams),
    placeholderData: (previous) => previous,
  });

  const categoriesParams = { start: period.start, end: period.end, type: filters.type };
  const categoriesQuery = useQuery({
    queryKey: ["transactions", "categories", categoriesParams],
    queryFn: () => listTransactionCategories(categoriesParams),
  });

  const hasActiveFilters = Boolean(filters.type || filters.category || filters.search);
  const items = transactionsQuery.data?.items ?? [];
  const total = transactionsQuery.data?.total ?? 0;
  const isEmpty = transactionsQuery.isSuccess && total === 0;
  // A última página pode ficar vazia depois de uma exclusão (o `total` cai,
  // o `offset` guardado não): oferece "Anterior" em vez de auto-navegar —
  // TransactionsPagination já desabilita "Próxima" quando `offset >= total`.
  const isTrailingEmptyPage = transactionsQuery.isSuccess && items.length === 0 && total > 0 && offset > 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Transações</h1>
          <p className="text-sm text-muted">Lançamentos do período selecionado no topo da tela.</p>
        </div>
        <div className="flex items-center gap-2">
          <ExportButton start={period.start} end={period.end} hasActiveFilters={hasActiveFilters} />
          <Button type="button" onClick={openCreate}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Nova transação
          </Button>
        </div>
      </div>

      <TransactionFilters value={filters} onChange={updateFilters} categories={categoriesQuery.data ?? []} />

      {transactionsQuery.isError ? (
        <ErrorState onRetry={() => transactionsQuery.refetch()} />
      ) : isEmpty ? (
        <EmptyState
          icon={Receipt}
          title={hasActiveFilters ? "Nenhuma transação encontrada" : "Nenhuma transação no período"}
          description={
            hasActiveFilters
              ? "Ajuste os filtros para ver outros lançamentos."
              : "Cadastre o primeiro lançamento deste período."
          }
          action={
            <Button type="button" onClick={openCreate}>
              Nova transação
            </Button>
          }
        />
      ) : (
        <>
          {isTrailingEmptyPage ? (
            <EmptyState
              icon={Receipt}
              title="Esta página não tem mais lançamentos"
              description="Alguém excluiu itens desta faixa — volte para a página anterior."
            />
          ) : (
            <TransactionsTable
              transactions={items}
              loading={transactionsQuery.isLoading}
              sort={sort}
              onSortChange={updateSort}
              onEdit={openEdit}
            />
          )}
          <TransactionsPagination total={total} limit={LIMIT} offset={offset} onOffsetChange={setOffset} />
        </>
      )}

      <TransactionFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        editing={editing}
        categorySuggestions={categoriesQuery.data ?? []}
      />
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-32 w-full" />
    </div>
  );
}
