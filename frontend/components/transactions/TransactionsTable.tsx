"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, ArrowUpDown, Pencil, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { deleteTransaction } from "@/lib/api/transactions";
import { describeError } from "@/lib/errors";
import { formatBRL, formatDateTimeSP } from "@/lib/format";
import { useToast } from "@/lib/toast";
import type { TransactionResponse } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { SourceBadge } from "@/components/transactions/SourceBadge";

/** `created_at` também é aceito pelo back-end (ORDERABLE_COLUMNS), mas não tem coluna visível aqui para o clique ordenar por ele. */
export type SortableColumn = "occurred_at" | "amount" | "description" | "category";

export interface SortState {
  orderBy: SortableColumn;
  order: "asc" | "desc";
}

const COLUMNS: { key: SortableColumn; label: string }[] = [
  { key: "occurred_at", label: "Data" },
  { key: "description", label: "Descrição" },
  { key: "category", label: "Categoria" },
  { key: "amount", label: "Valor" },
];

/** Janela de desfazer antes da exclusão de fato ir ao servidor — igual à duração padrão do toast (lib/toast.tsx), para as duas coisas expirarem juntas. */
const UNDO_WINDOW_MS = 5000;

export function TransactionsTable({
  transactions,
  loading,
  sort,
  onSortChange,
  onEdit,
}: {
  transactions: TransactionResponse[];
  loading: boolean;
  sort: SortState;
  onSortChange: (sort: SortState) => void;
  onEdit: (transaction: TransactionResponse) => void;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [hiddenIds, setHiddenIds] = useState<Set<string>>(new Set());
  const [confirmTarget, setConfirmTarget] = useState<TransactionResponse | null>(null);
  const pendingTimers = useRef(new Map<string, ReturnType<typeof setTimeout>>());

  // Timers pendentes disparariam a exclusão de qualquer jeito mesmo se a
  // tela desmontar — não cancelamos no cleanup de propósito, só evitamos
  // vazamento óbvio limpando a referência.
  useEffect(() => {
    const timers = pendingTimers.current;
    return () => timers.clear();
  }, []);

  const deleteMutation = useMutation({
    mutationFn: deleteTransaction,
    onError: (error, id) => {
      setHiddenIds((current) => {
        const next = new Set(current);
        next.delete(id);
        return next;
      });
      toast.show({ variant: "error", title: "Não foi possível excluir", description: describeError(error).message });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions", "list"] });
    },
  });

  function toggleSort(column: SortableColumn) {
    if (sort.orderBy === column) {
      onSortChange({ orderBy: column, order: sort.order === "asc" ? "desc" : "asc" });
    } else {
      onSortChange({ orderBy: column, order: "desc" });
    }
  }

  function confirmDelete() {
    const target = confirmTarget;
    if (!target) {
      return;
    }
    setConfirmTarget(null);
    setHiddenIds((current) => new Set(current).add(target.id));
    const timer = setTimeout(() => {
      pendingTimers.current.delete(target.id);
      deleteMutation.mutate(target.id);
    }, UNDO_WINDOW_MS);
    pendingTimers.current.set(target.id, timer);
    toast.show({
      variant: "info",
      title: "Transação excluída",
      description: target.description,
      action: {
        label: "Desfazer",
        onClick: () => {
          const pending = pendingTimers.current.get(target.id);
          if (pending) {
            clearTimeout(pending);
            pendingTimers.current.delete(target.id);
          }
          setHiddenIds((current) => {
            const next = new Set(current);
            next.delete(target.id);
            return next;
          });
        },
      },
    });
  }

  if (loading) {
    return (
      <div className="space-y-2 rounded-lg border border-border p-4">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-9 w-full" />
        ))}
      </div>
    );
  }

  const visibleRows = transactions.filter((transaction) => !hiddenIds.has(transaction.id));

  return (
    <>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-border bg-surface text-xs uppercase text-muted">
            <tr>
              {COLUMNS.map((column) => (
                <th key={column.key} className="px-3 py-2 font-medium">
                  <button
                    type="button"
                    onClick={() => toggleSort(column.key)}
                    className="flex items-center gap-1 hover:text-surface-foreground"
                  >
                    {column.label}
                    <SortIcon active={sort.orderBy === column.key} order={sort.order} />
                  </button>
                </th>
              ))}
              <th className="px-3 py-2 font-medium">Origem</th>
              <th className="px-3 py-2 text-right font-medium">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {visibleRows.map((transaction) => (
              <tr key={transaction.id} className="hover:bg-surface/60">
                <td className="whitespace-nowrap px-3 py-2 text-foreground">
                  {formatDateTimeSP(transaction.occurred_at)}
                </td>
                <td className="px-3 py-2 text-foreground">{transaction.description}</td>
                <td className="px-3 py-2 text-muted">{transaction.category ?? "Sem categoria"}</td>
                <td
                  className={`whitespace-nowrap px-3 py-2 text-right font-medium tabular-nums ${
                    transaction.type === "income" ? "text-success" : "text-danger"
                  }`}
                >
                  {transaction.type === "income" ? "+" : "-"}
                  {formatBRL(transaction.amount)}
                </td>
                <td className="px-3 py-2">
                  <SourceBadge source={transaction.source} />
                </td>
                <td className="px-3 py-2">
                  <div className="flex justify-end gap-1">
                    <button
                      type="button"
                      onClick={() => onEdit(transaction)}
                      aria-label={`Editar ${transaction.description}`}
                      className="rounded p-1.5 text-muted hover:bg-border/40 hover:text-surface-foreground"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmTarget(transaction)}
                      aria-label={`Excluir ${transaction.description}`}
                      className="rounded p-1.5 text-muted hover:bg-danger/10 hover:text-danger"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={confirmTarget !== null} onClose={() => setConfirmTarget(null)} title="Excluir transação">
        <div className="flex flex-col gap-4">
          <p className="text-sm text-muted">
            Excluir “{confirmTarget?.description}”? Você terá alguns segundos para desfazer logo em seguida.
          </p>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setConfirmTarget(null)}>
              Cancelar
            </Button>
            <Button type="button" variant="danger" onClick={confirmDelete}>
              Excluir
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

function SortIcon({ active, order }: { active: boolean; order: "asc" | "desc" }) {
  if (!active) {
    return <ArrowUpDown className="h-3 w-3 text-muted" aria-hidden="true" />;
  }
  return order === "asc" ? (
    <ArrowUp className="h-3 w-3" aria-hidden="true" />
  ) : (
    <ArrowDown className="h-3 w-3" aria-hidden="true" />
  );
}
