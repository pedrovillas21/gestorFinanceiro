"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { SessionExpiredError } from "@/lib/api/http";
import { isPasswordChangeRequiredError } from "@/lib/errors";
import { ThemeProvider } from "@/lib/theme";
import { ToastProvider, ToastViewport } from "@/lib/toast";

/**
 * Ponto único por onde todo erro de query/mutation passa (registrado no
 * QueryClient, não em cada tela) — cobre os dois jeitos de a sessão parar de
 * valer no meio do uso:
 *
 * - `SessionExpiredError` (lib/api/http.ts): o próprio `POST /api/auth/refresh`
 *   devolveu 401 — o servidor já encerrou a sessão (reuso detectado ou
 *   refresh token vencido). Não há mais nada a tentar: limpa o cookie local
 *   (best-effort, ele já morreu no servidor) e manda para o login.
 * - 403 do BFF (`isPasswordChangeRequiredError`, lib/errors.ts):
 *   `require_password_compliant_user` (backend/app/api/dependencies.py)
 *   barrou a chamada porque a conta está com `must_change_password=True`.
 *   O `DashboardShell` já redireciona assim que descobre isso via
 *   `GET /auth/me` — isto aqui é o reforço para uma query de tela disparada
 *   antes desse redirect terminar (ou de qualquer componente que não passe
 *   pelo shell).
 */
function handleAuthErrors(error: unknown): void {
  if (typeof window === "undefined") {
    return;
  }
  if (error instanceof SessionExpiredError) {
    fetch("/api/auth/logout", { method: "POST" }).finally(() => {
      // Navegação forçada de propósito, não um `router.push`: este callback
      // roda fora de qualquer componente (`onError` do QueryClient, sem
      // `useRouter()` disponível) e um logout duro deve mesmo descartar todo
      // estado de cliente — cache do React Query, formulários abertos etc.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/login";
    });
    return;
  }
  if (isPasswordChangeRequiredError(error) && window.location.pathname !== "/trocar-senha") {
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/trocar-senha";
  }
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, staleTime: 30_000 },
        },
        queryCache: new QueryCache({ onError: handleAuthErrors }),
        mutationCache: new MutationCache({ onError: handleAuthErrors }),
      }),
  );

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          {children}
          <ToastViewport />
        </ToastProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
