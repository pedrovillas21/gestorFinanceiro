import { describe, expect, it } from "vitest";

import { describeApiError, normalizeDetail } from "./errors";

describe("normalizeDetail", () => {
  it("mantém como está a mensagem de erro de negócio (string)", () => {
    const result = normalizeDetail("E-mail já cadastrado");
    expect(result.message).toBe("E-mail já cadastrado");
    expect(result.fieldErrors).toEqual([]);
  });

  it("normaliza o array de erros de validação do Pydantic", () => {
    // Formato real de PATCH /investments/movements/{id} em 422 (exc.errors()).
    const detail = [
      { loc: ["body", "new_password"], msg: "A nova senha deve ser diferente da atual", type: "value_error" },
      { loc: ["body", "quantity"], msg: "ensure this value is greater than 0", type: "greater_than" },
    ];
    const result = normalizeDetail(detail);
    expect(result.fieldErrors).toHaveLength(2);
    expect(result.fieldErrors[0]).toEqual({
      path: "body.new_password",
      message: "A nova senha deve ser diferente da atual",
    });
    expect(result.message).toContain("A nova senha deve ser diferente da atual");
  });

  it("devolve message nulo quando o detail está ausente ou vazio", () => {
    expect(normalizeDetail(undefined).message).toBeNull();
    expect(normalizeDetail(null).message).toBeNull();
    expect(normalizeDetail([]).message).toBeNull();
  });
});

describe("describeApiError", () => {
  it("usa a mensagem específica em português quando não há detail utilizável", () => {
    expect(describeApiError(429, undefined).message).toMatch(/tentativas/i);
    expect(describeApiError(404, undefined).message).toMatch(/não encontrado/i);
    expect(describeApiError(503, undefined).message).toMatch(/indisponível/i);
  });

  it("prioriza a mensagem vinda do detail sobre o fallback genérico do status", () => {
    expect(describeApiError(409, "Ativo já cadastrado").message).toBe("Ativo já cadastrado");
  });

  it("cai no fallback genérico para um status sem mensagem própria mapeada", () => {
    expect(describeApiError(418, undefined).message).toBe("Erro inesperado. Tente novamente.");
  });
});
