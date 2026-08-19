import Decimal from "decimal.js";

/**
 * Formatação de valores decimais (BRL, percentual) e datas.
 *
 * Regra dura do projeto: nunca formatar a partir de `Number()`. Preços de
 * ativos têm 6 casas decimais e quantidades 8 (backend/app/api/v1/investments.py
 * `_movement_values`); um double de 64 bits não representa esses valores com
 * exatidão, e o back-end já entrega tudo como string (Decimal serializa como
 * string no JSON — confirmado em backend/tests/test_api_integration.py). Todo
 * o caminho abaixo usa decimal.js e manipulação de string, ponto a ponto.
 */

function groupThousands(digits: string): string {
  const groups: string[] = [];
  for (let end = digits.length; end > 0; end -= 3) {
    groups.unshift(digits.slice(Math.max(0, end - 3), end));
  }
  return groups.join(".");
}

function toDecimal(value: string | Decimal): Decimal {
  return value instanceof Decimal ? value : new Decimal(value);
}

export interface FormatBRLOptions {
  /** Prefixa "+" em valores positivos (útil para ganho/perda). Padrão: false. */
  signed?: boolean;
}

/** Formata um valor decimal (string ou Decimal) como BRL, ex.: "R$ 1.234.567,90". */
export function formatBRL(input: string | Decimal, options: FormatBRLOptions = {}): string {
  const value = toDecimal(input);
  const isNegative = value.isNegative();
  const fixed = value.abs().toFixed(2);
  const [integerPart, fractionPart] = fixed.split(".");
  const sign = isNegative ? "-" : options.signed ? "+" : "";
  return `${sign}R$ ${groupThousands(integerPart)},${fractionPart}`;
}

export interface FormatPercentOptions {
  decimals?: number;
  /** Prefixa "+" em valores positivos. Padrão: true — percentuais de retorno costumam precisar do sinal. */
  signed?: boolean;
}

/** Formata uma fração ou taxa já em percentual (ex.: "3.5" -> "+3,50%"). */
export function formatPercent(input: string | Decimal, options: FormatPercentOptions = {}): string {
  const { decimals = 2, signed = true } = options;
  const value = toDecimal(input);
  const isNegative = value.isNegative();
  const fixed = value.abs().toFixed(decimals);
  const sign = isNegative ? "-" : signed ? "+" : "";
  return `${sign}${fixed.replace(".", ",")}%`;
}

/** Formata uma quantidade (ações, cotas) sem casas fixas artificiais, até `maxDecimals`. */
export function formatQuantity(input: string | Decimal, maxDecimals = 8): string {
  const value = toDecimal(input);
  const fixed = value.toFixed(maxDecimals);
  const trimmed = fixed.includes(".") ? fixed.replace(/0+$/, "").replace(/\.$/, "") : fixed;
  const isNegative = trimmed.startsWith("-");
  const [integerPart, fractionPart] = (isNegative ? trimmed.slice(1) : trimmed).split(".");
  const grouped = groupThousands(integerPart);
  return `${isNegative ? "-" : ""}${grouped}${fractionPart ? `,${fractionPart}` : ""}`;
}

const TIMEZONE = "America/Sao_Paulo";

const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  timeZone: TIMEZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  timeZone: TIMEZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

/** Data e hora no fuso America/Sao_Paulo, ex.: "17/08/2026 14:30". */
export function formatDateTimeSP(value: string | Date): string {
  return dateTimeFormatter.format(value instanceof Date ? value : new Date(value));
}

/** Só a data, no fuso America/Sao_Paulo, ex.: "17/08/2026". */
export function formatDateSP(value: string | Date): string {
  return dateFormatter.format(value instanceof Date ? value : new Date(value));
}

/**
 * Emite ISO 8601 sempre com offset explícito (nunca "Z"), no fuso local do
 * navegador. Investimentos rejeitam data ingênua com 422 (backend/app/api/v1/
 * investments.py `_as_utc`); transações e dashboard interpretam data ingênua
 * como America/Sao_Paulo. Emitir sempre com offset evita as duas armadilhas
 * de uma vez, em qualquer módulo.
 */
export function toIsoWithOffset(date: Date = new Date()): string {
  const pad = (value: number, width = 2) => String(value).padStart(width, "0");

  const offsetMinutesTotal = -date.getTimezoneOffset();
  const offsetSign = offsetMinutesTotal >= 0 ? "+" : "-";
  const offsetAbs = Math.abs(offsetMinutesTotal);
  const offset = `${offsetSign}${pad(Math.floor(offsetAbs / 60))}:${pad(offsetAbs % 60)}`;

  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  const seconds = pad(date.getSeconds());
  const milliseconds = pad(date.getMilliseconds(), 3);

  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}.${milliseconds}${offset}`;
}
