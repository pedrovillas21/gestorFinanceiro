import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { readSession } from "@/lib/session/cookies";

/**
 * Guard server-side: só confere se há cookie de sessão (refresh token) e
 * redireciona para /login se não houver. Não chama o back-end aqui — ver
 * DashboardShell para o porquê (renovação de sessão é responsabilidade do
 * cliente, não do render deste Server Component).
 */
export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const session = await readSession();
  if (!session) {
    redirect("/login");
  }

  return <DashboardShell>{children}</DashboardShell>;
}
