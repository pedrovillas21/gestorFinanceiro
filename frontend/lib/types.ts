/**
 * Espelho dos schemas Pydantic do back-end (backend/app/schemas/*.py).
 *
 * Campos `Decimal` do back-end serializam como STRING no JSON (confirmado em
 * backend/tests/test_api_integration.py: `created.json()["amount"] == "10.01"`),
 * nunca como number — por isso todo valor monetário/quantidade aqui é `string`.
 * Formatar a partir dessas strings é o trabalho de lib/format.ts; nunca passar
 * por `Number()` no caminho.
 *
 * Datas (`datetime`/`date` do Pydantic) também serializam como string ISO.
 */

// ---------------------------------------------------------------------------
// Auth (backend/app/schemas/auth.py)
// ---------------------------------------------------------------------------

export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  /** Opaco e rotacionado a cada POST /auth/refresh — guardar sempre o último recebido. */
  refresh_token: string;
  refresh_expires_at: string;
  /** Identifica a linha desta sessão em GET /auth/sessions. Não é credencial. */
  session_id: string;
  user: UserResponse;
}

export interface SessionResponse {
  id: string;
  user_agent: string | null;
  /** Numa sessão ativa, é a última atividade (cada renovação cria linha nova). */
  created_at: string;
  expires_at: string;
}

export interface MessageResponse {
  message: string;
}

// ---------------------------------------------------------------------------
// Transações (backend/app/schemas/transaction.py)
// ---------------------------------------------------------------------------

export type TransactionType = "income" | "expense";

/** `source` é string livre no back-end; só `web`/`telegram`/`import` são emitidos hoje. */
export type TransactionSource = "web" | "telegram" | "import" | (string & {});

export interface TransactionResponse {
  id: string;
  description: string;
  amount: string;
  category: string | null;
  type: TransactionType;
  payment_method: string | null;
  occurred_at: string;
  created_at: string;
  source: TransactionSource;
}

export interface TransactionListResponse {
  items: TransactionResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface CategorySummary {
  category: string;
  amount: string;
}

export interface FinancialSummary {
  income: string;
  expense: string;
  balance: string;
  by_category: CategorySummary[];
  by_category_type: TransactionType;
  start: string | null;
  end: string | null;
}

export interface CategoryOption {
  category: string;
  count: number;
}

export type TimeseriesGranularity = "day" | "week" | "month";

export interface TimeseriesPoint {
  /** Data local (America/Sao_Paulo) em que o período começa. */
  period: string;
  income: string;
  expense: string;
  balance: string;
}

export interface TimeseriesResponse {
  granularity: TimeseriesGranularity;
  points: TimeseriesPoint[];
  start: string | null;
  end: string | null;
}

// ---------------------------------------------------------------------------
// Importação (backend/app/schemas/import_job.py)
// ---------------------------------------------------------------------------

export type ImportJobStatus = "pending" | "processing" | "completed" | "failed" | (string & {});

export interface ImportJobResponse {
  id: string;
  filename: string;
  status: ImportJobStatus;
  total_rows: number;
  imported_rows: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ImportJobListResponse {
  items: ImportJobResponse[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// Investimentos (backend/app/schemas/investment.py)
// ---------------------------------------------------------------------------

export type AssetType = "stock" | "fii" | "etf" | "bdr" | "crypto" | "bond" | "fund" | "other";

export type MovementType =
  | "purchase"
  | "sale"
  | "dividend"
  | "jcp"
  | "fii_income"
  | "split"
  | "reverse_split"
  | "bonus"
  | "subscription"
  | "spinoff"
  | "merger";

export type TradeKind = "swing_trade" | "day_trade";

export interface AssetResponse {
  id: string;
  ticker: string;
  name: string | null;
  asset_type: AssetType;
  currency: string;
  created_at: string;
}

export interface MovementResponse {
  id: string;
  asset_id: string;
  movement_type: MovementType;
  occurred_at: string;
  quantity: string | null;
  unit_price: string | null;
  costs: string;
  gross_amount: string | null;
  net_amount: string | null;
  factor: string | null;
  trade_kind: TradeKind | null;
  fx_rate: string | null;
  fx_rate_date: string | null;
  notes: string | null;
  created_at: string;
}

export interface SnapshotResponse {
  total_value: string;
  net_cash_flow: string;
  captured_at: string;
}

export interface QuoteResponse {
  price: string;
  currency: string;
  provider: string;
  collected_at: string;
  stale: boolean;
}

export interface PositionResponse {
  asset: AssetResponse;
  quantity: string;
  average_price: string | null;
  invested_cost: string;
  realized_gain: string;
  dividends_gross: string;
  dividends_net: string;
  sales_proceeds: string;
  quote: QuoteResponse | null;
  /** Nulo é estado de negócio (posição sem cotação), nunca renderizar como 0. */
  market_value: string | null;
  unrealized_gain: string | null;
  return_on_cost: string | null;
}

export interface PortfolioResponse {
  positions: PositionResponse[];
  total_market_value: string | null;
  total_invested_cost: string;
  total_realized_gain: string;
  total_unrealized_gain: string | null;
  return_on_cost: string | null;
  twr: string | null;
  twr_annualized: string | null;
  mwr: string | null;
  /** Nota metodológica fixa — sempre vem preenchida, é rodapé permanente da seção. */
  profitability_note: string;
}

export interface QuoteRefreshResponse {
  updated: number;
  failed_tickers: string[];
  collected_at: string;
}

// ---------------------------------------------------------------------------
// Telegram (backend/app/schemas/telegram.py)
// ---------------------------------------------------------------------------

export interface TelegramLinkResponse {
  deep_link: string;
  expires_at: string;
  consent_version: string;
  privacy_policy_url: string;
}

export interface PrivacyPolicyResponse {
  version: string;
  title: string;
  published_at: string;
  content: string;
  content_sha256: string;
  privacy_policy_url: string;
}

export interface TelegramUnlinkResponse {
  message: string;
  unlinked_at: string;
  consent_version: string | null;
  consented_at: string | null;
}

export interface TelegramLinkStatus {
  linked: boolean;
  linked_at: string | null;
  consent_version: string | null;
  consented_at: string | null;
}

// ---------------------------------------------------------------------------
// Calculadora (backend/app/schemas/calculator.py)
// ---------------------------------------------------------------------------

export interface CompoundInterestPoint {
  month: number;
  invested: string;
  interest: string;
  total: string;
}

export interface CompoundInterestResponse {
  monthly_rate: string;
  total_invested: string;
  total_interest: string;
  final_value: string;
  schedule: CompoundInterestPoint[];
}
