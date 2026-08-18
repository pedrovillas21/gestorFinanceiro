import { describe, expect, it } from "vitest";

import { PASSWORD_REQUIREMENTS, changePasswordSchema, isPasswordCompliant, registerSchema } from "./auth";

/**
 * Espelha backend/tests/test_issue_hardening.py
 * (test_register_rejects_password_without_full_complexity /
 * test_register_accepts_password_with_full_complexity) — mesma tabela de
 * casos, para as duas pontas nunca divergirem sobre o que é uma senha válida.
 */
describe("isPasswordCompliant", () => {
  it.each([
    ["semmaiuscula1!", false], // falta maiúscula
    ["SEMMINUSCULA1!", false], // falta minúscula
    ["SemNumeroAqui!", false], // falta dígito
    ["SemEspecial123", false], // falta caractere especial
    ["Curta1!", false], // menos de 8 caracteres
    ["Senha-Forte1", true],
  ])("%s -> %s", (password, expected) => {
    expect(isPasswordCompliant(password)).toBe(expected);
  });

  it("expõe uma checklist com os 5 requisitos, cada um checável isoladamente", () => {
    expect(PASSWORD_REQUIREMENTS).toHaveLength(5);
    const results = PASSWORD_REQUIREMENTS.map((requirement) => requirement.test("Senha-Forte1"));
    expect(results.every(Boolean)).toBe(true);
  });
});

describe("registerSchema", () => {
  const base = {
    email: "pessoa@example.com",
    password: "Senha-Forte1",
    confirmPassword: "Senha-Forte1",
    full_name: "Pessoa",
  };

  it("aceita uma senha em conformidade com confirmação igual", () => {
    expect(registerSchema.safeParse(base).success).toBe(true);
  });

  it("rejeita quando a confirmação diverge", () => {
    const result = registerSchema.safeParse({ ...base, confirmPassword: "Outra-Senha1" });
    expect(result.success).toBe(false);
  });

  it("rejeita senha sem requisitos de complexidade", () => {
    const result = registerSchema.safeParse({
      ...base,
      password: "semrequisitos",
      confirmPassword: "semrequisitos",
    });
    expect(result.success).toBe(false);
  });
});

/** Usado em /trocar-senha (força de troca de senha legada) e na futura tela de Configurações. */
describe("changePasswordSchema", () => {
  const base = {
    current_password: "senha-antiga-fraca",
    new_password: "Senha-Forte1",
    confirmNewPassword: "Senha-Forte1",
    revoke_other_sessions: true,
  };

  it("aceita uma nova senha em conformidade, diferente da atual, com confirmação igual", () => {
    expect(changePasswordSchema.safeParse(base).success).toBe(true);
  });

  it("rejeita quando a nova senha é igual à atual", () => {
    const result = changePasswordSchema.safeParse({
      ...base,
      current_password: "Senha-Forte1",
      new_password: "Senha-Forte1",
      confirmNewPassword: "Senha-Forte1",
    });
    expect(result.success).toBe(false);
  });

  it("rejeita quando a confirmação da nova senha diverge", () => {
    const result = changePasswordSchema.safeParse({ ...base, confirmNewPassword: "Outra-Senha1" });
    expect(result.success).toBe(false);
  });
});
