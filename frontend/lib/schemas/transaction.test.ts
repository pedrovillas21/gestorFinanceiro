import { describe, expect, it } from "vitest";

import { transactionFormSchema } from "./transaction";

/** Espelha as restrições de `TransactionBase` (backend/app/schemas/transaction.py): amount > 0, no máximo 2 casas. */
describe("transactionFormSchema", () => {
  const base = {
    description: "Supermercado",
    amount: "123.45",
    category: "Alimentação",
    type: "expense" as const,
    payment_method: "Cartão",
    occurred_at: "2026-08-18T10:00",
  };

  it("aceita um lançamento válido", () => {
    expect(transactionFormSchema.safeParse(base).success).toBe(true);
  });

  it("aceita categoria e forma de pagamento vazias (campos opcionais)", () => {
    const result = transactionFormSchema.safeParse({ ...base, category: "", payment_method: "" });
    expect(result.success).toBe(true);
  });

  it.each([
    ["0", false],
    ["-10.00", false],
    ["10.999", false], // mais de 2 casas
    ["abc", false],
    ["", false],
    ["0.01", true],
    ["10", true],
    ["10.5", true],
  ])("amount %s -> válido: %s", (amount, expected) => {
    expect(transactionFormSchema.safeParse({ ...base, amount }).success).toBe(expected);
  });

  it("rejeita descrição vazia", () => {
    expect(transactionFormSchema.safeParse({ ...base, description: "  " }).success).toBe(false);
  });

  it("rejeita tipo fora de income|expense", () => {
    expect(transactionFormSchema.safeParse({ ...base, type: "outro" }).success).toBe(false);
  });
});
