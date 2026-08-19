import { http } from "@/lib/api/http";
import type { PortfolioResponse } from "@/lib/types";

/**
 * Cliente de `/investments` sobre o BFF. Só `getPortfolio` por enquanto — o
 * bloco resumo da carteira na Visão geral (plan, Fase 4) é o único consumidor
 * até a Fase 6/7 trazerem ativos, movimentações e o resto do módulo.
 *
 * `GET /investments/portfolio` não aceita período: é o estado atual da
 * carteira, não uma janela de tempo (backend/app/api/v1/investments.py).
 */
export async function getPortfolio(): Promise<PortfolioResponse> {
  const { data } = await http.get<PortfolioResponse>("/investments/portfolio");
  return data;
}
