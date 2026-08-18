import { http } from "@/lib/api/http";
import { PAGINATION } from "@/lib/api/pagination";
import type { CategoryOption, TransactionListResponse, TransactionResponse, TransactionType } from "@/lib/types";

/**
 * Cliente de `/transactions` sobre o BFF (lib/api/http.ts, baseURL
 * `/api/bff`). Contrato em backend/app/api/v1/transactions.py.
 */

export interface ListTransactionsParams {
  start?: string;
  end?: string;
  category?: string;
  type?: TransactionType;
  search?: string;
  order_by?: "occurred_at" | "amount" | "description" | "category" | "created_at";
  order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export async function listTransactions(params: ListTransactionsParams = {}): Promise<TransactionListResponse> {
  const { data } = await http.get<TransactionListResponse>("/transactions", {
    params: { limit: PAGINATION.transactions.defaultLimit, ...params },
  });
  return data;
}

export interface ListTransactionCategoriesParams {
  start?: string;
  end?: string;
  type?: TransactionType;
}

/** GET /transactions/categories — só categorias já usadas; nulos/vazios não geram opção (decisão do back-end). */
export async function listTransactionCategories(
  params: ListTransactionCategoriesParams = {},
): Promise<CategoryOption[]> {
  const { data } = await http.get<CategoryOption[]>("/transactions/categories", { params });
  return data;
}

export interface TransactionPayload {
  description: string;
  amount: string;
  category: string | null;
  type: TransactionType;
  payment_method: string | null;
  occurred_at: string;
}

/** `source` é definido pelo servidor ("web") — nunca faz parte do payload enviado daqui. */
export async function createTransaction(payload: TransactionPayload): Promise<TransactionResponse> {
  const { data } = await http.post<TransactionResponse>("/transactions", payload);
  return data;
}

export type TransactionUpdatePayload = Partial<TransactionPayload>;

/**
 * PATCH é parcial no back-end, mas `description`, `amount`, `type` e
 * `occurred_at` nunca podem ir `null` (422) — o formulário (TransactionForm)
 * sempre valida esses quatro como obrigatórios, então enviar o objeto
 * completo é seguro; só `category`/`payment_method` podem virar `null`.
 */
export async function updateTransaction(
  id: string,
  payload: TransactionUpdatePayload,
): Promise<TransactionResponse> {
  const { data } = await http.patch<TransactionResponse>(`/transactions/${id}`, payload);
  return data;
}

export async function deleteTransaction(id: string): Promise<void> {
  await http.delete(`/transactions/${id}`);
}

export type ExportFormat = "csv" | "pdf";

export interface ExportTransactionsParams {
  format: ExportFormat;
  start?: string;
  end?: string;
}

export interface ExportResult {
  blob: Blob;
  filename: string;
}

const EXPORT_FILENAME_FALLBACK: Record<ExportFormat, string> = {
  csv: "transacoes.csv",
  pdf: "transacoes.pdf",
};

/** Extrai o nome de `Content-Disposition: attachment; filename="x.csv"` — cai no nome padrão se o cabeçalho vier ausente. */
function parseFilename(contentDisposition: string | undefined, format: ExportFormat): string {
  if (!contentDisposition) {
    return EXPORT_FILENAME_FALLBACK[format];
  }
  const match = /filename="?([^";]+)"?/i.exec(contentDisposition);
  return match?.[1] ?? EXPORT_FILENAME_FALLBACK[format];
}

/**
 * GET /transactions/export só aceita `format`, `start` e `end` — nunca
 * `category`/`type`/`search` (plan, Fase 3). Baixado via blob porque é uma
 * rota autenticada: um `<a href>` simples não carrega o cookie de sessão do
 * jeito que o axios do BFF precisa para injetar o Bearer.
 */
export async function exportTransactions(params: ExportTransactionsParams): Promise<ExportResult> {
  const response = await http.get<Blob>("/transactions/export", { params, responseType: "blob" });
  return {
    blob: response.data,
    filename: parseFilename(response.headers["content-disposition"], params.format),
  };
}
