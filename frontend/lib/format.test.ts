import Decimal from "decimal.js";
import { describe, expect, it } from "vitest";

import { formatBRL, formatPercent, toIsoWithOffset } from "./format";

describe("formatBRL", () => {
  it("formata a partir de uma string decimal, com milhar e arredondamento para 2 casas", () => {
    expect(formatBRL("1234567.895")).toBe("R$ 1.234.567,90");
  });

  it("preserva o sinal negativo", () => {
    expect(formatBRL("-42.5")).toBe("-R$ 42,50");
  });

  it("aceita o sinalizador de positivo explícito", () => {
    expect(formatBRL("10", { signed: true })).toBe("+R$ 10,00");
  });

  it("mantém precisão exata para valores acima de Number.MAX_SAFE_INTEGER", () => {
    // 2^53 ~ 9.007199254740992e15 — bem menor que o valor abaixo. Passar por
    // Number() aqui arredondaria dígitos que a string exata não perde.
    const raw = "90071992547409991234.555";
    expect(formatBRL(raw)).toBe("R$ 90.071.992.547.409.991.234,56");
  });

  it("aceita um Decimal diretamente, sem precisar converter para string antes", () => {
    expect(formatBRL(new Decimal("1000.005"))).toBe("R$ 1.000,01"); // ROUND_HALF_UP
  });
});

describe("formatPercent", () => {
  it("formata com sinal por padrão", () => {
    expect(formatPercent("3.5")).toBe("+3,50%");
    expect(formatPercent("-1.2")).toBe("-1,20%");
  });

  it("omite o sinal quando signed: false", () => {
    expect(formatPercent("3.5", { signed: false })).toBe("3,50%");
  });
});

describe("toIsoWithOffset", () => {
  it("sempre emite offset explícito, nunca 'Z'", () => {
    const iso = toIsoWithOffset(new Date("2026-08-17T12:00:00.000Z"));
    expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}$/);
    expect(iso.endsWith("Z")).toBe(false);
  });

  it("usa agora por padrão quando nenhuma data é passada", () => {
    const before = Date.now();
    const iso = toIsoWithOffset();
    const parsed = new Date(iso).getTime();
    expect(parsed).toBeGreaterThanOrEqual(before - 1000);
    expect(parsed).toBeLessThanOrEqual(Date.now() + 1000);
  });
});
