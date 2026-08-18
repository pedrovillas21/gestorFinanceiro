"use client";

import { ChevronDown, LogOut, Settings, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { logout } from "@/lib/api/auth";
import type { UserResponse } from "@/lib/types";

/**
 * `<details>` nativo em vez de estado + listener de clique fora: fecha
 * sozinho ao perder foco/clicar fora, sem JS extra, e continua acessível por
 * teclado de graça.
 */
export function UserMenu({ user }: { user: UserResponse }) {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  async function handleLogout() {
    setSigningOut(true);
    try {
      await logout();
    } finally {
      router.push("/login");
      router.refresh();
    }
  }

  return (
    <details className="relative">
      <summary className="flex cursor-pointer list-none items-center gap-2 rounded-md px-2 py-1.5 text-sm text-surface-foreground hover:bg-surface [&::-webkit-details-marker]:hidden">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <UserRound className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="hidden max-w-[10rem] truncate sm:inline">{user.full_name || user.email}</span>
        <ChevronDown className="h-4 w-4 text-muted" aria-hidden="true" />
      </summary>

      <div className="absolute right-0 z-50 mt-2 w-56 rounded-md border border-border bg-surface p-1 shadow-lg">
        <div className="truncate px-3 py-2 text-xs text-muted">{user.email}</div>
        <Link
          href="/configuracoes"
          className="flex items-center gap-2 rounded px-3 py-2 text-sm text-surface-foreground hover:bg-border/40"
        >
          <Settings className="h-4 w-4" aria-hidden="true" />
          Configurações
        </Link>
        <button
          type="button"
          onClick={handleLogout}
          disabled={signingOut}
          className="flex w-full items-center gap-2 rounded px-3 py-2 text-sm text-danger hover:bg-danger/10 disabled:opacity-60"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
          {signingOut ? "Saindo…" : "Sair"}
        </button>
      </div>
    </details>
  );
}
