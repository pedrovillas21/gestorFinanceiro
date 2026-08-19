import Decimal from "decimal.js";

import { formatBRL, formatPercent } from "@/lib/format";
import type { CategorySummary } from "@/lib/types";

/**
 * Tabela compacta das categorias do período (plan, Fase 4): valor e
 * participação percentual sobre o total das categorias listadas, calculada
 * no front com decimal.js — o back-end só devolve o valor absoluto por
 * categoria (`FinancialSummary.by_category`), já ordenado do maior para o
 * menor.
 */
export function CategoryTable({ categories }: { categories: CategorySummary[] }) {
  const total = categories.reduce((sum, item) => sum.plus(item.amount), new Decimal(0));

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted">
            <th className="px-3 py-2 font-medium">Categoria</th>
            <th className="px-3 py-2 text-right font-medium">Valor</th>
            <th className="px-3 py-2 text-right font-medium">Participação</th>
          </tr>
        </thead>
        <tbody>
          {categories.map((item) => {
            const share = total.isZero() ? new Decimal(0) : new Decimal(item.amount).div(total).mul(100);
            return (
              <tr key={item.category} className="border-b border-border last:border-b-0">
                <td className="px-3 py-2 text-surface-foreground">{item.category}</td>
                <td className="px-3 py-2 text-right tabular-nums text-surface-foreground">{formatBRL(item.amount)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-muted">
                  {formatPercent(share, { signed: false, decimals: 1 })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
