import Decimal from "decimal.js";
import { z } from "zod";

/**
 * Espelha `TransactionBase`/`TransactionCreate` (backend/app/schemas/transaction.py):
 * `description` 1–255, `amount` > 0 com no máximo 2 casas, `category` e
 * `payment_method` opcionais (até 100/50), `type` income|expense. O back-end
 * valida `amount` como Decimal, nunca float — mesma razão pela qual a
 * validação aqui usa decimal.js em vez de `Number()` (lib/format.ts explica
 * a regra dura do projeto).
 */
function isValidMoneyString(value: string): boolean {
  try {
    const decimal = new Decimal(value);
    return decimal.isFinite() && decimal.greaterThan(0) && decimal.decimalPlaces() <= 2;
  } catch {
    return false;
  }
}

export const transactionFormSchema = z.object({
  description: z.string().trim().min(1, "Informe a descrição").max(255, "Máximo de 255 caracteres"),
  amount: z
    .string()
    .trim()
    .min(1, "Informe o valor")
    .refine(isValidMoneyString, "O valor deve ser maior que zero, com até 2 casas decimais"),
  category: z.string().trim().max(100, "Máximo de 100 caracteres").optional().or(z.literal("")),
  type: z.enum(["income", "expense"]),
  payment_method: z.string().trim().max(50, "Máximo de 50 caracteres").optional().or(z.literal("")),
  // Valor de <input type="datetime-local"> ("YYYY-MM-DDTHH:mm"); convertido
  // para ISO com offset (lib/format.ts toIsoWithOffset) só na submissão.
  occurred_at: z.string().min(1, "Informe a data"),
});

export type TransactionFormInput = z.infer<typeof transactionFormSchema>;
