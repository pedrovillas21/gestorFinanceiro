"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchCurrentUser } from "@/lib/api/auth";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

/**
 * O guard de `(dashboard)/layout.tsx` só confere se existe cookie de sessão
 * (leitura, sem chamar o back-end — `cookies().set()` não funciona durante
 * render de Server Component, então ele não pode tentar renovar nada). Quem
 * busca o usuário de verdade é este componente, client-side, via
 * `fetchCurrentUser` (lib/api/auth.ts): se o access token já expirou (aba
 * aberta há mais de 30 minutos), o 401 aciona o single-flight de refresh
 * (lib/api/http.ts) e a requisição repete sozinha — sem novo login. Se o
 * refresh também falhar, `SessionExpiredError` sobe até o `onError` global do
 * QueryClient (app/providers.tsx), que faz o logout duro.
 */
export function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const { data: user } = useQuery({
    queryKey: ["session", "me"],
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  // Login/cadastro já mandam quem está com `must_change_password` direto para
  // /trocar-senha (ver LoginForm.tsx) — isto cobre quem já estava com o
  // dashboard aberto quando a conta foi migrada, ou entrou direto pela URL.
  useEffect(() => {
    if (user?.must_change_password) {
      router.replace("/trocar-senha");
    }
  }, [user, router]);

  return (
    <div className="flex min-h-full flex-1">
      <Sidebar open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar user={user} onMenuClick={() => setMobileNavOpen(true)} />
        <main className="flex-1 overflow-x-auto p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
