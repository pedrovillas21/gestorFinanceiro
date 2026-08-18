import { Settings } from "lucide-react";

import { ComingSoon } from "@/components/ui/ComingSoon";

export default function SettingsPage() {
  return (
    <ComingSoon
      icon={Settings}
      title="Configurações"
      description="Conta, troca de senha, dispositivos conectados e Telegram chegam numa próxima fase."
    />
  );
}
