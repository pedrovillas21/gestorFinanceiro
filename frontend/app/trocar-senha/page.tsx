import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { ForcePasswordChangeForm } from "@/components/auth/ForcePasswordChangeForm";
import { readSession } from "@/lib/session/cookies";

export const metadata: Metadata = { title: "Atualize sua senha" };

/**
 * Rota própria, fora de `(dashboard)`: de propósito sem sidebar/topbar — a
 * pessoa não deveria conseguir navegar para o resto do app com uma senha
 * sinalizada como fora da regra atual (`User.must_change_password`, ver
 * backend/app/models/user.py). O gatilho para cair aqui é client-side: login/
 * cadastro (LoginForm/RegisterForm) checam `user.must_change_password` na
 * resposta, e o DashboardShell confere de novo a cada carga do shell — cobre
 * quem já estava logado quando a conta foi migrada.
 */
export default async function ForcePasswordChangePage() {
  const session = await readSession();
  if (!session) {
    redirect("/login");
  }

  return (
    <div className="flex flex-1 items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-sm">
        <p className="mb-6 text-center text-lg font-semibold text-surface-foreground">
          Gestor Financeiro
        </p>
        <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">
          <div className="mb-6 space-y-1 text-center">
            <h1 className="text-xl font-semibold text-surface-foreground">Atualize sua senha</h1>
            <p className="text-sm text-muted">
              Sua senha atual não atende aos requisitos de segurança da conta. Escolha uma nova
              antes de continuar.
            </p>
          </div>
          <ForcePasswordChangeForm />
        </div>
      </div>
    </div>
  );
}
