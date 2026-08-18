import { Receipt } from "lucide-react";

import { ComingSoon } from "@/components/ui/ComingSoon";

export default function TransactionsPage() {
  return (
    <ComingSoon
      icon={Receipt}
      title="Transações"
      description="Tabela, filtros, importação e exportação chegam nas próximas fases."
    />
  );
}
