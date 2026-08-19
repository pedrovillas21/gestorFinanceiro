"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatBRL } from "@/lib/format";
import { formatPeriodLong, formatPeriodShort } from "@/lib/timeseries";
import type { TimeseriesGranularity, TimeseriesPoint } from "@/lib/types";

/**
 * Gráfico de evolução (plan, Fase 4): receita, despesa e saldo ao longo do
 * período, uma linha por identidade — cores fixas de sinal (mesma convenção
 * dos KPIs), sempre na mesma ordem, com legenda porque são três séries.
 * `points` já vem sem buracos: períodos sem lançamento chegam com zero
 * (backend/app/services/timeseries.py `build_series`).
 */
const SERIES: Array<{ key: "income" | "expense" | "balance"; label: string; color: string }> = [
  { key: "income", label: "Receitas", color: "var(--success)" },
  { key: "expense", label: "Despesas", color: "var(--danger)" },
  { key: "balance", label: "Saldo", color: "var(--primary)" },
];

interface ChartRow {
  period: string;
  income: number;
  expense: number;
  balance: number;
}

function toRows(points: TimeseriesPoint[]): ChartRow[] {
  return points.map((point) => ({
    period: point.period,
    income: Number(point.income),
    expense: Number(point.expense),
    balance: Number(point.balance),
  }));
}

function EvolutionTooltip({
  active,
  label,
  granularity,
  points,
}: {
  active?: boolean;
  label?: string;
  granularity: TimeseriesGranularity;
  points: TimeseriesPoint[];
}) {
  if (!active || !label) {
    return null;
  }
  const point = points.find((item) => item.period === label);
  if (!point) {
    return null;
  }
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 text-sm shadow-sm">
      <p className="mb-1 font-medium text-surface-foreground">{formatPeriodLong(label, granularity)}</p>
      {SERIES.map((series) => (
        <p key={series.key} className="flex items-center justify-between gap-4 tabular-nums">
          <span className="flex items-center gap-1.5 text-muted">
            <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: series.color }} aria-hidden="true" />
            {series.label}
          </span>
          <span className="text-surface-foreground">{formatBRL(point[series.key])}</span>
        </p>
      ))}
    </div>
  );
}

export function EvolutionChart({
  points,
  granularity,
}: {
  points: TimeseriesPoint[];
  granularity: TimeseriesGranularity;
}) {
  const rows = toRows(points);
  const showDots = rows.length <= 60;

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 4, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="var(--border)" vertical={false} />
          <XAxis
            dataKey="period"
            tickFormatter={(value: string) => formatPeriodShort(value, granularity)}
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            interval="preserveStartEnd"
            minTickGap={24}
          />
          <YAxis
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            width={72}
            tickFormatter={(value: number) => formatBRL(String(value))}
          />
          <Tooltip content={<EvolutionTooltip granularity={granularity} points={points} />} />
          <Legend
            formatter={(value: string) => <span className="text-xs text-surface-foreground">{value}</span>}
            iconType="line"
            iconSize={12}
          />
          {SERIES.map((series) => (
            <Line
              key={series.key}
              type="monotone"
              dataKey={series.key}
              name={series.label}
              stroke={series.color}
              strokeWidth={2}
              dot={showDots ? { r: 2.5, fill: series.color, strokeWidth: 0 } : false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
