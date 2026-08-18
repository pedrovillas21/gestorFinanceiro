import { describe, expect, it } from "vitest";

import { computePeriodRange, readPeriodFromSearchParams } from "./period";

/**
 * `start` inclusivo / `end` exclusivo é o contrato de todo o back-end
 * (`occurred_at < end`) — o caso que mais importa acertar aqui.
 */
describe("computePeriodRange", () => {
  const reference = new Date(2026, 7, 18, 15, 30); // terça-feira, 18/08/2026, 15:30 local

  it("today: começa às 00:00 do dia e termina às 00:00 do dia seguinte", () => {
    const range = computePeriodRange("today", reference);
    expect(range.start).toMatch(/^2026-08-18T00:00:00\.000/);
    expect(range.end).toMatch(/^2026-08-19T00:00:00\.000/);
  });

  it("month: começa no dia 1 e termina no dia 1 do mês seguinte (end exclusivo)", () => {
    const range = computePeriodRange("month", reference);
    expect(range.start).toMatch(/^2026-08-01T00:00:00\.000/);
    expect(range.end).toMatch(/^2026-09-01T00:00:00\.000/);
  });

  it("year: começa em 1º de janeiro e termina em 1º de janeiro do ano seguinte", () => {
    const range = computePeriodRange("year", reference);
    expect(range.start).toMatch(/^2026-01-01T00:00:00\.000/);
    expect(range.end).toMatch(/^2027-01-01T00:00:00\.000/);
  });

  it("quarter: cobre os 3 meses terminando no mês corrente, não os últimos 90 dias corridos", () => {
    const range = computePeriodRange("quarter", reference);
    expect(range.start).toMatch(/^2026-06-01T00:00:00\.000/);
    expect(range.end).toMatch(/^2026-09-01T00:00:00\.000/);
  });

  it("week: começa numa segunda-feira e cobre exatamente 7 dias", () => {
    const range = computePeriodRange("week", reference);
    const start = new Date(range.start);
    const end = new Date(range.end);
    expect(start.getDay()).toBe(1); // segunda-feira
    expect((end.getTime() - start.getTime()) / (24 * 60 * 60 * 1000)).toBe(7);
  });

  it("custom: end vira o dia seguinte à data final escolhida, mesmo incluindo o dia inteiro", () => {
    const range = computePeriodRange("custom", reference, "2026-08-01", "2026-08-15");
    expect(range.start).toMatch(/^2026-08-01T00:00:00\.000/);
    expect(range.end).toMatch(/^2026-08-16T00:00:00\.000/);
  });

  it("custom sem as duas datas ainda preenchidas mantém o preset mas usa o mês corrente como janela provisória", () => {
    const range = computePeriodRange("custom", reference);
    expect(range.preset).toBe("custom");
    expect(range.start).toMatch(/^2026-08-01T00:00:00\.000/);
    expect(range.end).toMatch(/^2026-09-01T00:00:00\.000/);
  });

  it("toda combinação start/end sempre emite offset explícito, nunca 'Z'", () => {
    for (const preset of ["today", "week", "month", "quarter", "year"] as const) {
      const range = computePeriodRange(preset, reference);
      expect(range.start).not.toMatch(/Z$/);
      expect(range.end).not.toMatch(/Z$/);
      expect(range.start).toMatch(/[+-]\d{2}:\d{2}$/);
      expect(range.end).toMatch(/[+-]\d{2}:\d{2}$/);
    }
  });
});

describe("readPeriodFromSearchParams", () => {
  const reference = new Date(2026, 7, 18, 15, 30);

  it("sem parâmetros, cai no mês corrente", () => {
    const range = readPeriodFromSearchParams({}, reference);
    expect(range.preset).toBe("month");
  });

  it("preset reconhecido recalcula a janela a partir de 'agora', ignorando start/end antigos na URL", () => {
    const range = readPeriodFromSearchParams({ period: "year", start: "lixo", end: "lixo" }, reference);
    expect(range.preset).toBe("year");
    expect(range.start).toMatch(/^2026-01-01T00:00:00\.000/);
  });

  it("preset 'custom' com start/end usa exatamente o que veio na URL", () => {
    const range = readPeriodFromSearchParams(
      { period: "custom", start: "2026-08-01T00:00:00.000-03:00", end: "2026-08-16T00:00:00.000-03:00" },
      reference,
    );
    expect(range).toEqual({
      preset: "custom",
      start: "2026-08-01T00:00:00.000-03:00",
      end: "2026-08-16T00:00:00.000-03:00",
    });
  });

  it("preset desconhecido cai no mês corrente", () => {
    const range = readPeriodFromSearchParams({ period: "quinzena" }, reference);
    expect(range.preset).toBe("month");
  });
});
