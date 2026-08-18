import { TrendingUp } from "lucide-react";

import { ComingSoon } from "@/components/ui/ComingSoon";

export default function InvestmentsPage() {
  return (
    <ComingSoon
      icon={TrendingUp}
      title="Investimentos"
      description="Ativos, movimentações, carteira e cotações chegam nas próximas fases."
    />
  );
}
