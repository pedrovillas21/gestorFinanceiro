/**
 * Limites de paginação por rota — nunca uma constante global. Cada rota do
 * back-end define seu próprio padrão e teto (ver backend/app/api/v1/*.py);
 * usar o valor errado não dá erro nenhum na maioria dos casos, só trunca a
 * lista em silêncio (ou, em /transactions/imports, devolve 422 se o `limit`
 * passar do teto de outra rota, ex.: 200 nessa rota).
 */
export const PAGINATION = {
  /** GET /transactions — envelope {items, total, limit, offset}. */
  transactions: { defaultLimit: 50, maxLimit: 200 },
  /** GET /transactions/imports — envelope {items, total, limit, offset}. */
  transactionImports: { defaultLimit: 20, maxLimit: 100 },
  /** GET /investments/assets — lista pura, sem total. */
  investmentAssets: { defaultLimit: 200, maxLimit: 500 },
  /** GET /investments/assets/{id}/movements — lista pura, sem total. */
  investmentMovements: { defaultLimit: 200, maxLimit: 500 },
  /** GET /auth/sessions — lista pura, sem total. */
  authSessions: { defaultLimit: 50, maxLimit: 200 },
  /** GET /investments/snapshots — lista pura, só `limit` (sem `offset`); corta as fotografias mais antigas. */
  investmentSnapshots: { defaultLimit: 365, maxLimit: 1000 },
} as const;

export type PaginationKey = keyof typeof PAGINATION;
