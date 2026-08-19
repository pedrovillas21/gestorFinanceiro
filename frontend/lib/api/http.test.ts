import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Aceite crítico do 05 §7: com access token expirado, disparar várias
 * requisições ao mesmo tempo tem que produzir um único POST /auth/refresh. A
 * falha aqui desloga o usuário de todos os aparelhos (detecção de reuso no
 * back-end — 07 §6 item 18).
 *
 * Testa `ensureFreshSession` diretamente (não o transporte do axios): é o
 * mesmo caminho que o interceptor de lib/api/http.ts usa, e evita simular a
 * camada HTTP inteira para provar a dedupe.
 */

function setEpochCookie(value: string | null): void {
  document.cookie = "gf_sess_epoch=; Max-Age=0; path=/";
  if (value !== null) {
    document.cookie = `gf_sess_epoch=${value}; path=/`;
  }
}

beforeEach(() => {
  vi.resetModules();
  setEpochCookie(null);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ensureFreshSession", () => {
  it("dispara exatamente um POST /api/auth/refresh para N chamadas concorrentes", async () => {
    const fetchMock = vi.fn(
      () =>
        new Promise((resolve) => {
          setTimeout(() => resolve({ ok: true }), 5);
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { ensureFreshSession } = await import("./http");

    await Promise.all(Array.from({ length: 8 }, () => ensureFreshSession("epoch-a")));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/refresh", expect.objectContaining({ method: "POST" }));
  });

  it("vira logout duro quando o próprio refresh devolve 401, sem tentativa nova", async () => {
    const fetchMock = vi.fn(async () => ({ ok: false }));
    vi.stubGlobal("fetch", fetchMock);

    const { ensureFreshSession, SessionExpiredError } = await import("./http");

    const results = await Promise.allSettled([
      ensureFreshSession("epoch-a"),
      ensureFreshSession("epoch-a"),
      ensureFreshSession("epoch-a"),
    ]);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    for (const result of results) {
      expect(result.status).toBe("rejected");
      if (result.status === "rejected") {
        expect(result.reason).toBeInstanceOf(SessionExpiredError);
      }
    }
  });

  it("pula o refresh quando outra aba já renovou (epoch mudou desde o 401 observado)", async () => {
    setEpochCookie("epoch-b");
    const fetchMock = vi.fn(async () => ({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const { ensureFreshSession } = await import("./http");

    await expect(ensureFreshSession("epoch-a")).resolves.toBeUndefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sem epoch conhecido ainda (primeiro 401 da aba), sempre renova", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const { ensureFreshSession } = await import("./http");

    await ensureFreshSession(null);

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("chamadas sequenciais (não concorrentes) disparam um refresh cada", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const { ensureFreshSession } = await import("./http");

    await ensureFreshSession("epoch-a");
    await ensureFreshSession("epoch-a");

    // A promessa compartilhada se limpa (`finally`) após cada resolução —
    // uma chamada nova, depois da anterior já ter terminado, é uma
    // renovação legítima, não uma duplicata da mesma rajada.
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
