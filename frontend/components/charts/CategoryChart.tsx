"use client";

import Decimal from "decimal.js";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatBRL } from "@/lib/format";
import type { CategorySummary, TransactionType } from "@/lib/types";

/**
 * Gráfico de barras horizontais por categoria (plan, Fase 4), a partir de
 * `FinancialSummary.by_category` — já vem ordenado do maior para o menor
 * (backend/app/api/v1/dashboard.py). Uma única cor por gráfico: é uma única
 * medida (valor) repartida por categoria, não identidades distintas
 * competindo por atenção, então a cor segue o sinal do tipo agregado
 * (`by_category_type`) em vez de uma paleta categórica nova — mesma
 * convenção de verde/vermelho já usada nos KPIs.
 */
const MAX_BARS = 8;
const OTHERS_LABEL = "Outras";

const TYPE_COLOR: Record<TransactionType, string> = {
  income: "var(--success)",
  expense: "var(--danger)",
};

interface ChartRow {
  category: string;
  /** String decimal, só para exibição (tooltip) — nunca usada em aritmética. */
  amount: string;
  /** Número derivado só para posicionar a barra na escala do gráfico; a precisão de ponto flutuante aqui não afeta nenhum valor exibido. */
  value: number;
}

function toRow(category: string, amount: string): ChartRow {
  return { category, amount, value: Number(amount) };
}

function buildRows(categories: CategorySummary[]): ChartRow[] {
  if (categories.length <= MAX_BARS) {
    return categories.map((item) => toRow(item.category, item.amount));
  }
  const head = categories.slice(0, MAX_BARS - 1).map((item) => toRow(item.category, item.amount));
  const rest = categories.slice(MAX_BARS - 1);
  const othersTotal = rest.reduce((sum, item) => sum.plus(item.amount), new Decimal(0));
  return [...head, toRow(OTHERS_LABEL, othersTotal.toFixed(2))];
}

function CategoryTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ChartRow }> }) {
  if (!active || !payload?.length) {
    return null;
  }
  const row = payload[0].payload;
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 text-sm shadow-sm">
      <p className="font-medium text-surface-foreground">{row.category}</p>
      <p className="tabular-nums text-muted">{formatBRL(row.amount)}</p>
    </div>
  );
}

export function CategoryChart({ categories, type }: { categories: CategorySummary[]; type: TransactionType }) {
  const rows = buildRows(categories);
  const color = TYPE_COLOR[type];
  const height = Math.max(160, rows.length * 36 + 24);

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 4 }} barCategoryGap="24%">
          <CartesianGrid horizontal={false} stroke="var(--border)" />
          <XAxis
            type="number"
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            tickFormatter={(value: number) => formatBRL(String(value))}
          />
          <YAxis
            type="category"
            dataKey="category"
            width={110}
            tick={{ fill: "var(--surface-foreground)", fontSize: 12 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
          />
          <Tooltip content={<CategoryTooltip />} cursor={{ fill: "var(--border)", opacity: 0.3 }} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={22}>
            {rows.map((row) => (
              <Cell key={row.category} fill={color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
