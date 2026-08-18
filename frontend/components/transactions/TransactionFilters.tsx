"use client";

import { useEffect, useState } from "react";

import type { CategoryOption, TransactionType } from "@/lib/types";
import { Select } from "@/components/ui/Select";
import { TextField } from "@/components/ui/TextField";

export interface TransactionFiltersValue {
  type?: TransactionType;
  category?: string;
  search: string;
}

const SEARCH_DEBOUNCE_MS = 400;

/**
 * Busca com debounce: a busca do back-end é ILIKE sobre descrição e
 * categoria (backend/app/api/v1/transactions.py `_conditions`) — refazer a
 * consulta a cada tecla sobrecarregaria à toa. Tipo e categoria propagam
 * na hora (são seleções discretas, não digitação).
 */
export function TransactionFilters({
  value,
  onChange,
  categories,
}: {
  value: TransactionFiltersValue;
  onChange: (value: TransactionFiltersValue) => void;
  categories: CategoryOption[];
}) {
  const [searchInput, setSearchInput] = useState(value.search);

  useEffect(() => {
    if (searchInput === value.search) {
      return;
    }
    const timer = setTimeout(() => onChange({ ...value, search: searchInput }), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="w-52">
        <TextField
          label="Buscar"
          placeholder="Descrição ou categoria..."
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
        />
      </div>
      <div className="w-36">
        <Select
          label="Tipo"
          value={value.type ?? ""}
          onChange={(event) =>
            onChange({ ...value, type: (event.target.value || undefined) as TransactionType | undefined })
          }
        >
          <option value="">Todos</option>
          <option value="income">Receita</option>
          <option value="expense">Despesa</option>
        </Select>
      </div>
      <div className="w-48">
        <Select
          label="Categoria"
          value={value.category ?? ""}
          onChange={(event) => onChange({ ...value, category: event.target.value || undefined })}
        >
          <option value="">Todas as categorias</option>
          {categories.map((option) => (
            <option key={option.category} value={option.category}>
              {option.category} ({option.count})
            </option>
          ))}
        </Select>
      </div>
    </div>
  );
}
