"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import type { TransactionPayload } from "@/lib/api/transactions";
import { describeError } from "@/lib/errors";
import { toIsoWithOffset } from "@/lib/format";
import { transactionFormSchema, type TransactionFormInput } from "@/lib/schemas/transaction";
import type { CategoryOption, TransactionResponse } from "@/lib/types";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { TextField } from "@/components/ui/TextField";

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** ISO com offset (lib/format.ts) -> valor local de <input type="datetime-local">, sem passar por UTC. */
function toDateTimeLocalValue(iso: string): string {
  const date = new Date(iso);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export interface TransactionFormProps {
  /** Presente = edição; ausente = criação. */
  initial?: TransactionResponse;
  onSubmit: (payload: TransactionPayload) => Promise<void>;
  onCancel: () => void;
  /** Sugestões para o campo Categoria (GET /transactions/categories do período atual). */
  categorySuggestions?: CategoryOption[];
}

export function TransactionForm({ initial, onSubmit, onCancel, categorySuggestions = [] }: TransactionFormProps) {
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<TransactionFormInput>({
    resolver: zodResolver(transactionFormSchema),
    defaultValues: initial
      ? {
          description: initial.description,
          amount: initial.amount,
          category: initial.category ?? "",
          type: initial.type,
          payment_method: initial.payment_method ?? "",
          occurred_at: toDateTimeLocalValue(initial.occurred_at),
        }
      : {
          description: "",
          amount: "",
          category: "",
          type: "expense",
          payment_method: "",
          occurred_at: toDateTimeLocalValue(toIsoWithOffset()),
        },
  });

  async function submit(values: TransactionFormInput) {
    setFormError(null);
    try {
      await onSubmit({
        description: values.description,
        amount: values.amount,
        category: values.category?.trim() ? values.category.trim() : null,
        type: values.type,
        payment_method: values.payment_method?.trim() ? values.payment_method.trim() : null,
        // `new Date("YYYY-MM-DDTHH:mm")` já é interpretado no fuso local do
        // navegador (sem "Z"), então toIsoWithOffset emite o offset certo
        // sem reconversão — mesma convenção de lib/period.ts para datas custom.
        occurred_at: toIsoWithOffset(new Date(values.occurred_at)),
      });
    } catch (error) {
      setFormError(describeError(error).message);
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} noValidate className="flex flex-col gap-4">
      {formError ? <Alert variant="error">{formError}</Alert> : null}

      <Select label="Tipo" error={errors.type?.message} {...register("type")}>
        <option value="expense">Despesa</option>
        <option value="income">Receita</option>
      </Select>

      <TextField label="Descrição" error={errors.description?.message} {...register("description")} />

      <TextField
        label="Valor"
        type="number"
        step="0.01"
        min="0.01"
        inputMode="decimal"
        error={errors.amount?.message}
        {...register("amount")}
      />

      <TextField
        label="Categoria (opcional)"
        list="transaction-category-suggestions"
        error={errors.category?.message}
        {...register("category")}
      />
      <datalist id="transaction-category-suggestions">
        {categorySuggestions.map((option) => (
          <option key={option.category} value={option.category} />
        ))}
      </datalist>

      <TextField
        label="Forma de pagamento (opcional)"
        error={errors.payment_method?.message}
        {...register("payment_method")}
      />

      <TextField
        label="Data e hora"
        type="datetime-local"
        error={errors.occurred_at?.message}
        {...register("occurred_at")}
      />

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" loading={isSubmitting}>
          {initial ? "Salvar" : "Criar"}
        </Button>
      </div>
    </form>
  );
}
