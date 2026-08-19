import { http } from "@/lib/api/http";
import type { FinancialSummary, TimeseriesGranularity, TimeseriesResponse, TransactionType } from "@/lib/types";

/**
 * Cliente de `/dashboard` sobre o BFF. Contrato em
 * backend/app/api/v1/dashboard.py — nenhuma das duas rotas tem envelope de
 * paginação, e as duas aceitam `start`/`end` ingênuos (interpretados como
 * America/Sao_Paulo pelo back-end, diferente de investimentos).
 */

export interface SummaryParams {
  start?: string;
  end?: string;
  /** Escolhe o que `by_category` agrega; a resposta ecoa em `by_category_type`. Padrão do back-end: expense. */
  type?: TransactionType;
}

export async function getFinancialSummary(params: SummaryParams = {}): Promise<FinancialSummary> {
  const { data } = await http.get<FinancialSummary>("/dashboard/summary", { params });
  return data;
}

export interface TimeseriesParams {
  start?: string;
  end?: string;
  granularity?: TimeseriesGranularity;
}

export async function getFinancialTimeseries(params: TimeseriesParams = {}): Promise<TimeseriesResponse> {
  const { data } = await http.get<TimeseriesResponse>("/dashboard/timeseries", { params });
  return data;
}
