import { toIsoWithOffset } from "@/lib/format";

/**
 * Seletor de período global do dashboard (plan, Fase 2). Toda janela de
 * tempo do projeto é `start` inclusivo / `end` exclusivo
 * (`occurred_at < end`, backend/app/api/v1/transactions.py) — "Mês" manda o
 * primeiro dia do mês seguinte como `end`, nunca o último dia às 23:59:59.
 * As duas pontas sempre saem de `toIsoWithOffset` (lib/format.ts): nunca
 * "Z", sempre o offset local explícito, mesma regra que o resto do projeto.
 */

export type PeriodPreset = "today" | "week" | "month" | "quarter" | "year" | "custom";

export const PERIOD_PRESETS: readonly PeriodPreset[] = ["today", "week", "month", "quarter", "year", "custom"];

export const PERIOD_PRESET_LABELS: Record<PeriodPreset, string> = {
  today: "Hoje",
  week: "Semana",
  month: "Mês",
  quarter: "3 meses",
  year: "Ano",
  custom: "Personalizado",
};

export interface PeriodRange {
  preset: PeriodPreset;
  /** Inclusivo. */
  start: string;
  /** Exclusivo. */
  end: string;
}

function startOfDay(date: Date): Date {
  const result = new Date(date);
  result.setHours(0, 0, 0, 0);
  return result;
}

function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

function startOfMonth(date: Date, monthOffset = 0): Date {
  return new Date(date.getFullYear(), date.getMonth() + monthOffset, 1);
}

function startOfYear(date: Date, yearOffset = 0): Date {
  return new Date(date.getFullYear() + yearOffset, 0, 1);
}

/** Segunda-feira da semana corrente — semana ISO (segunda a domingo), não os últimos 7 dias. */
function startOfWeek(date: Date): Date {
  const day = date.getDay(); // 0 = domingo
  const diffToMonday = day === 0 ? -6 : 1 - day;
  return startOfDay(addDays(date, diffToMonday));
}

/**
 * Calcula `start`/`end` de um preset a partir de `reference` ("agora", por
 * padrão). Para `custom`, `customStart`/`customEnd` são datas `YYYY-MM-DD`
 * (valor de `<input type="date">`); `end` vira o dia seguinte à data
 * escolhida, para manter o contrato de exclusivo mesmo quando o usuário
 * pensa em "até o dia 15" incluindo o dia 15 inteiro.
 */
export function computePeriodRange(
  preset: PeriodPreset,
  reference: Date = new Date(),
  customStart?: string,
  customEnd?: string,
): PeriodRange {
  switch (preset) {
    case "today": {
      const start = startOfDay(reference);
      return { preset, start: toIsoWithOffset(start), end: toIsoWithOffset(addDays(start, 1)) };
    }
    case "week": {
      const start = startOfWeek(reference);
      return { preset, start: toIsoWithOffset(start), end: toIsoWithOffset(addDays(start, 7)) };
    }
    case "month": {
      const start = startOfMonth(reference);
      return { preset, start: toIsoWithOffset(start), end: toIsoWithOffset(startOfMonth(reference, 1)) };
    }
    case "quarter": {
      // "3 meses": mês corrente + 2 anteriores, terminando no início do
      // próximo mês — não os últimos 90 dias corridos.
      const start = startOfMonth(reference, -2);
      return { preset, start: toIsoWithOffset(start), end: toIsoWithOffset(startOfMonth(reference, 1)) };
    }
    case "year": {
      const start = startOfYear(reference);
      return { preset, start: toIsoWithOffset(start), end: toIsoWithOffset(startOfYear(reference, 1)) };
    }
    case "custom": {
      if (!customStart || !customEnd) {
        // Sem as duas datas ainda, usa a janela do mês corrente como valor
        // provisório — mas mantém `preset: "custom"`, para a UI continuar
        // mostrando os campos de data em vez de voltar para "Mês".
        const fallback = computePeriodRange("month", reference);
        return { preset: "custom", start: fallback.start, end: fallback.end };
      }
      const start = startOfDay(new Date(`${customStart}T00:00:00`));
      const endDay = startOfDay(new Date(`${customEnd}T00:00:00`));
      const end = addDays(endDay, 1);
      return { preset, start: toIsoWithOffset(start), end: toIsoWithOffset(end) };
    }
    default:
      return computePeriodRange("month", reference);
  }
}

export interface PeriodSearchParams {
  period?: string | null;
  start?: string | null;
  end?: string | null;
}

/** Lê o período da query string; cai no mês corrente se ausente ou inválido. */
export function readPeriodFromSearchParams(params: PeriodSearchParams, reference: Date = new Date()): PeriodRange {
  const preset = PERIOD_PRESETS.includes(params.period as PeriodPreset) ? (params.period as PeriodPreset) : null;

  if (preset === "custom" && params.start && params.end) {
    return { preset: "custom", start: params.start, end: params.end };
  }
  if (preset && preset !== "custom") {
    return computePeriodRange(preset, reference);
  }
  return computePeriodRange("month", reference);
}

export function periodToSearchParams(range: PeriodRange): Record<string, string> {
  return { period: range.preset, start: range.start, end: range.end };
}
