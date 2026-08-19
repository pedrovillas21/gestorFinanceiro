import type { TimeseriesGranularity } from "@/lib/types";

/**
 * Teto do back-end (backend/app/services/timeseries.py `MAX_POINTS`): acima
 * de 1000 pontos, `GET /dashboard/timeseries` devolve 422. Em vez de deixar o
 * usuário cair nesse erro escolhendo "Personalizado" com um intervalo grande,
 * a UI deriva a granularidade do tamanho do período (plan, Fase 4).
 */
const MAX_POINTS = 1000;

/**
 * Um ano inteiro (365 dias) ainda cabe em granularidade diária — só período
 * acima de ~2,7 anos precisa subir para semana, e só acima de ~19 anos para
 * mês. `start`/`end` são ISO com offset (lib/period.ts); a duração em dias
 * não depende de fuso porque é só a diferença entre os dois instantes.
 */
export function pickGranularity(startIso: string, endIso: string): TimeseriesGranularity {
  const days = Math.max(1, (new Date(endIso).getTime() - new Date(startIso).getTime()) / 86_400_000);
  if (days <= MAX_POINTS) {
    return "day";
  }
  if (days / 7 <= MAX_POINTS) {
    return "week";
  }
  return "month";
}

const MONTH_LABELS = [
  "jan",
  "fev",
  "mar",
  "abr",
  "mai",
  "jun",
  "jul",
  "ago",
  "set",
  "out",
  "nov",
  "dez",
];

/**
 * `period` chega como data de calendário pura ("AAAA-MM-DD", já em
 * America/Sao_Paulo — backend/app/services/timeseries.py `SeriesPoint`), não
 * um instante UTC. Formatar via `new Date(period)` interpretaria a string
 * como meia-noite UTC e, num fuso atrás de UTC como America/Sao_Paulo,
 * mostraria o dia anterior — por isso o parse é manual, por componente, sem
 * passar por `Date`/`Intl` com timezone.
 */
function parsePeriod(period: string): { year: number; month: number; day: number } {
  const [year, month, day] = period.split("-").map(Number);
  return { year, month, day };
}

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

/** Rótulo curto para o eixo do gráfico: "05/08" (dia/semana) ou "ago/26" (mês). */
export function formatPeriodShort(period: string, granularity: TimeseriesGranularity): string {
  const { year, month, day } = parsePeriod(period);
  if (granularity === "month") {
    return `${MONTH_LABELS[month - 1]}/${String(year).slice(2)}`;
  }
  return `${pad2(day)}/${pad2(month)}`;
}

/** Rótulo completo para o tooltip: "5 de agosto de 2026" ou "Semana de 05/08/2026" ou "Agosto de 2026". */
export function formatPeriodLong(period: string, granularity: TimeseriesGranularity): string {
  const { year, month, day } = parsePeriod(period);
  const monthName = MONTH_LABELS[month - 1];
  if (granularity === "month") {
    return `${monthName.charAt(0).toUpperCase()}${monthName.slice(1)} de ${year}`;
  }
  if (granularity === "week") {
    return `Semana de ${pad2(day)}/${pad2(month)}/${year}`;
  }
  return `${pad2(day)}/${pad2(month)}/${year}`;
}
