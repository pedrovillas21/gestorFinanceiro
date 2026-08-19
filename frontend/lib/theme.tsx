"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore } from "react";

/**
 * Tema claro/escuro com três estados: "light", "dark" e "system" (segue
 * `prefers-color-scheme`, sem atributo no `<html>` — ver app/globals.css).
 * Persistido em localStorage; aplicado via `data-theme` no elemento raiz,
 * porque Tailwind v4 não expõe um hook de tema pronto neste projeto.
 *
 * `useSyncExternalStore` em vez de `useState` + `useEffect`: localStorage só
 * existe no cliente, então o snapshot do servidor ("system") diverge do
 * valor real assim que a página hidrata. É exatamente o caso que essa API
 * resolve sem gambiarra — React reconcilia a divergência sozinho, sem o
 * padrão "setState dentro de efeito" (proibido pelo linter do projeto) nem
 * aviso de hydration mismatch.
 */
export type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "gf-theme";
const listeners = new Set<() => void>();

function readStoredTheme(): Theme {
  if (typeof window === "undefined") {
    return "system";
  }
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === "light" || stored === "dark" ? stored : "system";
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function getServerSnapshot(): Theme {
  return "system";
}

function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", theme);
  }
}

function writeTheme(theme: Theme): void {
  if (theme === "system") {
    window.localStorage.removeItem(STORAGE_KEY);
  } else {
    window.localStorage.setItem(STORAGE_KEY, theme);
  }
  for (const listener of listeners) {
    listener();
  }
}

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useSyncExternalStore(subscribe, readStoredTheme, getServerSnapshot);

  // Só manipula o DOM (sistema externo) — nunca chama setState aqui, o
  // estado em si já vem do useSyncExternalStore acima.
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => writeTheme(next), []);
  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme precisa estar dentro de <ThemeProvider>");
  }
  return context;
}
