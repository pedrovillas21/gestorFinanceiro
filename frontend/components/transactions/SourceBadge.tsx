import { FileSpreadsheet, Globe, HelpCircle, Send, type LucideIcon } from "lucide-react";

import type { TransactionSource } from "@/lib/types";

/**
 * Três origens emitidas hoje (web, telegram, import) mais um fallback para
 * qualquer outro valor: `source` é string livre no back-end (lib/types.ts),
 * e numa base migrada de planilha `import` é a maioria das linhas — um badge
 * binário renderizaria errado justamente no volume maior (plan, Fase 3).
 */
const SOURCE_META: Record<string, { label: string; icon: LucideIcon; className: string }> = {
  web: { label: "Web", icon: Globe, className: "bg-primary/10 text-primary" },
  telegram: { label: "Telegram", icon: Send, className: "bg-success/10 text-success" },
  import: { label: "Importação", icon: FileSpreadsheet, className: "bg-warning/10 text-warning" },
};

const UNKNOWN_META = { label: "Desconhecida", icon: HelpCircle, className: "bg-border/60 text-muted" };

export function SourceBadge({ source }: { source: TransactionSource }) {
  const meta = SOURCE_META[source] ?? UNKNOWN_META;
  const Icon = meta.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${meta.className}`}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      {meta.label}
    </span>
  );
}
