"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  PERIOD_PRESETS,
  PERIOD_PRESET_LABELS,
  computePeriodRange,
  periodToSearchParams,
  readPeriodFromSearchParams,
  type PeriodPreset,
} from "@/lib/period";

/**
 * Seletor de período global (plan, Fase 2): Hoje, Semana, Mês, 3 meses, Ano,
 * Personalizado — refletido na query string (`period`, `start`, `end`) para
 * links compartilháveis. `start`/`end` vão fixados na URL, não só o nome do
 * preset: um link de "Mês" compartilhado hoje precisa continuar apontando
 * para agosto/2026 amanhã, não recalcular para o mês em que for aberto.
 */
export function PeriodSelector() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const current = useMemo(
    () =>
      readPeriodFromSearchParams({
        period: searchParams.get("period"),
        start: searchParams.get("start"),
        end: searchParams.get("end"),
      }),
    [searchParams],
  );

  const [customStart, setCustomStart] = useState(() => toDateInputValue(current.start));
  const [customEnd, setCustomEnd] = useState(() => previousLocalDate(current.end));

  const hasRangeInUrl = searchParams.has("period") && searchParams.has("start") && searchParams.has("end");

  const applyRange = (preset: PeriodPreset, start?: string, end?: string) => {
    const range = computePeriodRange(preset, new Date(), start, end);
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(periodToSearchParams(range))) {
      params.set(key, value);
    }
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  // Sem período na URL ainda (primeira visita): grava o padrão (mês
  // corrente) para a tela nascer com um link já compartilhável.
  useEffect(() => {
    if (!hasRangeInUrl) {
      applyRange("month");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasRangeInUrl]);

  return (
    // `min-w-0` deixa este flex item encolher abaixo do conteúdo (o padrão do
    // flexbox é não encolher), senão os seis presets forçariam o Topbar a
    // quebrar linha em telas estreitas — o que empurrava tema/usuário para
    // fora do lugar (ver comentário em Topbar.tsx). Em vez disso os presets
    // rolam horizontalmente dentro da própria faixa.
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      <div className="flex flex-nowrap gap-1 overflow-x-auto rounded-md border border-border bg-surface p-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {PERIOD_PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            onClick={() => applyRange(preset)}
            aria-pressed={current.preset === preset}
            className={`shrink-0 rounded px-2.5 py-1 text-xs font-medium transition-colors ${
              current.preset === preset
                ? "bg-primary text-primary-foreground"
                : "text-muted hover:text-surface-foreground"
            }`}
          >
            {PERIOD_PRESET_LABELS[preset]}
          </button>
        ))}
      </div>

      {current.preset === "custom" ? (
        <div className="flex items-center gap-1.5 text-xs">
          <input
            type="date"
            value={customStart}
            onChange={(event) => {
              setCustomStart(event.target.value);
              if (event.target.value && customEnd) {
                applyRange("custom", event.target.value, customEnd);
              }
            }}
            className="rounded border border-border bg-background px-2 py-1 text-foreground"
            aria-label="Data inicial"
          />
          <span className="text-muted">até</span>
          <input
            type="date"
            value={customEnd}
            onChange={(event) => {
              setCustomEnd(event.target.value);
              if (customStart && event.target.value) {
                applyRange("custom", customStart, event.target.value);
              }
            }}
            className="rounded border border-border bg-background px-2 py-1 text-foreground"
            aria-label="Data final"
          />
        </div>
      ) : null}
    </div>
  );
}

/** A string já vem local (toIsoWithOffset) — os 10 primeiros caracteres já são a data local, sem novo parse. */
function toDateInputValue(isoWithOffset: string): string {
  return isoWithOffset.slice(0, 10);
}

/**
 * `end` é exclusivo; o campo de data final mostra o último dia incluído, não
 * o dia seguinte. `setDate`/`getDate` operam no fuso local do navegador —
 * mesma convenção do resto do projeto (lib/format.ts `toIsoWithOffset`) —
 * então o cálculo fica em componentes locais, nunca via `toISOString()`
 * (que converteria para UTC e poderia mudar o dia exibido).
 */
function previousLocalDate(isoWithOffset: string): string {
  const date = new Date(isoWithOffset);
  date.setDate(date.getDate() - 1);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
