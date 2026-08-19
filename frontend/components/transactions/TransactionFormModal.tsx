"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createTransaction, updateTransaction, type TransactionPayload } from "@/lib/api/transactions";
import { useToast } from "@/lib/toast";
import type { CategoryOption, TransactionResponse } from "@/lib/types";
import { Modal } from "@/components/ui/Modal";
import { TransactionForm } from "@/components/transactions/TransactionForm";

export function TransactionFormModal({
  open,
  onClose,
  editing,
  categorySuggestions,
}: {
  open: boolean;
  onClose: () => void;
  /** `null` = criação. */
  editing: TransactionResponse | null;
  categorySuggestions: CategoryOption[];
}) {
  const queryClient = useQueryClient();
  const toast = useToast();

  const createMutation = useMutation({ mutationFn: createTransaction });
  const updateMutation = useMutation({
    mutationFn: (payload: TransactionPayload) => updateTransaction(editing?.id ?? "", payload),
  });

  async function handleSubmit(payload: TransactionPayload) {
    if (editing) {
      await updateMutation.mutateAsync(payload);
      toast.show({ variant: "success", title: "Transação atualizada" });
    } else {
      await createMutation.mutateAsync(payload);
      toast.show({ variant: "success", title: "Transação criada" });
    }
    // Cobre tanto a lista (["transactions", "list", ...]) quanto as opções de
    // categoria (["transactions", "categories", ...]) — uma categoria nova
    // digitada aqui precisa aparecer no filtro sem precisar recarregar a tela.
    await queryClient.invalidateQueries({ queryKey: ["transactions"] });
    onClose();
  }

  return (
    <Modal open={open} onClose={onClose} title={editing ? "Editar transação" : "Nova transação"}>
      {/* `key` força remontar o formulário ao trocar de alvo (nova x editar
          outra linha) — defaultValues do react-hook-form só se aplicam na
          primeira montagem. */}
      {open ? (
        <TransactionForm
          key={editing?.id ?? "new"}
          initial={editing ?? undefined}
          onSubmit={handleSubmit}
          onCancel={onClose}
          categorySuggestions={categorySuggestions}
        />
      ) : null}
    </Modal>
  );
}
