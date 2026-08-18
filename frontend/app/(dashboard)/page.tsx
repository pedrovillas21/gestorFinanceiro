import { LayoutDashboard } from "lucide-react";

import { TelegramCard } from "@/components/dashboard/TelegramCard";
import { EmptyState } from "@/components/ui/EmptyState";

export default function OverviewPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Visão geral</h1>
        <p className="text-sm text-muted">
          Receitas, despesas e evolução do período selecionado no topo da tela.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <TelegramCard />
        <EmptyState
          icon={LayoutDashboard}
          title="KPIs e gráficos chegam na próxima fase"
          description="Cadastre sua primeira transação para começar a acompanhar seu financeiro aqui."
        />
      </div>
    </div>
  );
}
