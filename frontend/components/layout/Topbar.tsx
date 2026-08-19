"use client";

import { Menu } from "lucide-react";
import { Suspense } from "react";

import { PeriodSelector } from "@/components/dashboard/PeriodSelector";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { UserMenu } from "@/components/layout/UserMenu";
import { Skeleton } from "@/components/ui/Skeleton";
import type { UserResponse } from "@/lib/types";

export function Topbar({
  user,
  onMenuClick,
}: {
  user: UserResponse | undefined;
  onMenuClick: () => void;
}) {
  return (
    // `flex-wrap` sozinho quebraria o grupo tema/usuário para uma segunda
    // linha em telas estreitas e, sem mais nenhum item nessa linha,
    // `justify-between` degenera para `flex-start` — o menu do usuário nasce
    // colado na borda esquerda em vez da direita. `ml-auto` no último grupo
    // não depende de ter vizinhos na mesma linha: ele sempre empurra o grupo
    // para o fim, quebrado ou não.
    <header className="flex flex-wrap items-center gap-3 border-b border-border bg-surface px-4 py-3 sm:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        className="shrink-0 rounded-md p-2 text-muted hover:bg-border/40 md:hidden"
        aria-label="Abrir menu"
      >
        <Menu className="h-5 w-5" />
      </button>
      {/* useSearchParams exige um limite de Suspense (doc do Next 16). */}
      <Suspense fallback={null}>
        <PeriodSelector />
      </Suspense>

      <div className="ml-auto flex shrink-0 items-center gap-1">
        <ThemeToggle />
        {user ? <UserMenu user={user} /> : <Skeleton className="h-8 w-8 rounded-full" />}
      </div>
    </header>
  );
}
