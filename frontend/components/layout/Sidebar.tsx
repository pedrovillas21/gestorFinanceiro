"use client";

import { Calculator, LayoutDashboard, Receipt, Settings, TrendingUp, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import type { LucideIcon } from "lucide-react";

/** Só o período viaja entre telas — filtros próprios de cada tela (busca, ordenação) não fazem sentido fora dela. */
const PERIOD_PARAM_KEYS = ["period", "start", "end"];

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Visão geral", icon: LayoutDashboard },
  { href: "/transacoes", label: "Transações", icon: Receipt },
  { href: "/investimentos", label: "Investimentos", icon: TrendingUp },
  { href: "/ferramentas/juros-compostos", label: "Ferramentas", icon: Calculator },
  { href: "/configuracoes", label: "Configurações", icon: Settings },
];

/** "Visão geral" só está ativo em "/" exato — as demais rotas usam prefixo (ex.: /investimentos/ativos/123). */
function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const periodQuery = new URLSearchParams();
  for (const key of PERIOD_PARAM_KEYS) {
    const value = searchParams.get(key);
    if (value) {
      periodQuery.set(key, value);
    }
  }
  const periodSuffix = periodQuery.toString() ? `?${periodQuery.toString()}` : "";

  return (
    <>
      {open ? (
        <button
          type="button"
          aria-label="Fechar menu"
          onClick={onClose}
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
        />
      ) : null}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border bg-surface transition-transform md:static md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-4">
          <span className="text-sm font-semibold text-surface-foreground">Gestor Financeiro</span>
          <button type="button" onClick={onClose} className="rounded p-1 text-muted md:hidden" aria-label="Fechar menu">
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex flex-1 flex-col gap-1 p-3">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = isActive(pathname, href);
            return (
              <Link
                key={href}
                href={`${href}${periodSuffix}`}
                onClick={onClose}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-surface-foreground hover:bg-border/40"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
