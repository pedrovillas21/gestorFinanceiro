"use client";

import { Monitor, Moon, Sun } from "lucide-react";

import { useTheme, type Theme } from "@/lib/theme";

const ORDER: Theme[] = ["system", "light", "dark"];
const ICON: Record<Theme, typeof Sun> = { system: Monitor, light: Sun, dark: Moon };
const LABEL: Record<Theme, string> = { system: "Tema: automático", light: "Tema: claro", dark: "Tema: escuro" };

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const Icon = ICON[theme];

  return (
    <button
      type="button"
      onClick={() => setTheme(ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length])}
      title={LABEL[theme]}
      aria-label={LABEL[theme]}
      className="rounded-md p-2 text-muted hover:bg-surface hover:text-surface-foreground"
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
    </button>
  );
}
