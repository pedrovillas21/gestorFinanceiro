import Decimal from "decimal.js";
import { ArrowDownCircle, ArrowUpCircle, Wallet, type LucideIcon } from "lucide-react";

import { formatBRL } from "@/lib/format";

/**
 * Três KPIs do topo da Visão geral (plan, Fase 4): receitas, despesas e
 * saldo, coloridos por sinal. Receita e despesa usam sempre a mesma cor
 * (verde/vermelho, o sinal delas nunca muda); só o saldo depende do valor.
 */
export function KpiCards({ income, expense, balance }: { income: string; expense: string; balance: string }) {
  const balanceValue = new Decimal(balance);
  const balanceClass = balanceValue.isNegative()
    ? "text-danger"
    : balanceValue.isZero()
      ? "text-surface-foreground"
      : "text-success";

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <KpiCard icon={ArrowUpCircle} iconClass="text-success" label="Receitas" value={formatBRL(income)} valueClass="text-success" />
      <KpiCard icon={ArrowDownCircle} iconClass="text-danger" label="Despesas" value={formatBRL(expense)} valueClass="text-danger" />
      <KpiCard icon={Wallet} iconClass={balanceClass} label="Saldo" value={formatBRL(balance)} valueClass={balanceClass} />
    </div>
  );
}

function KpiCard({
  icon: Icon,
  iconClass,
  label,
  value,
  valueClass,
}: {
  icon: LucideIcon;
  iconClass: string;
  label: string;
  value: string;
  valueClass: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-center gap-2 text-sm font-medium text-muted">
        <Icon className={`h-4 w-4 ${iconClass}`} aria-hidden="true" />
        {label}
      </div>
      <p className={`mt-2 text-2xl font-semibold tabular-nums ${valueClass}`}>{value}</p>
    </div>
  );
}
