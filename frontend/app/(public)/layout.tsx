import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { readSession } from "@/lib/session/cookies";

/**
 * Shell das páginas públicas (login, cadastro). Redireciona quem já tem
 * cookie de sessão para o dashboard — só checa a presença do refresh token
 * (barato, sem chamar o back-end); se o cookie estiver revogado no servidor,
 * o guard do (dashboard)/layout.tsx e o interceptor de refresh do lib/api/
 * http.ts resolvem isso na primeira chamada de API, não aqui.
 */
export default async function PublicLayout({ children }: { children: ReactNode }) {
  const session = await readSession();
  if (session) {
    redirect("/");
  }

  return (
    <div className="flex flex-1 items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-sm">
        <p className="mb-6 text-center text-lg font-semibold text-surface-foreground">
          Gestor Financeiro
        </p>
        <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">{children}</div>
      </div>
    </div>
  );
}
