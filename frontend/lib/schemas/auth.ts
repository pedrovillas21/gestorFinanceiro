import { z } from "zod";

// Mesma regra do backend/app/schemas/auth.py (EMAIL_PATTERN).
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * A senha valida 8–72 BYTES em UTF-8, não caracteres: um acento ocupa mais de
 * 1 byte, então `password.length <= 72` deixaria passar senhas que o backend
 * rejeita com 422. `TextEncoder` mede o mesmo jeito que `str.encode("utf-8")`
 * no Python.
 */
function utf8ByteLength(value: string): number {
  return new TextEncoder().encode(value).length;
}

export interface PasswordRequirement {
  id: string;
  /** Rótulo curto exibido na checklist do cadastro e na dica do login. */
  label: string;
  test: (value: string) => boolean;
}

/**
 * Espelha `_validate_password_complexity` em backend/app/schemas/auth.py:
 * mínimo 8 caracteres, 1 minúscula, 1 maiúscula, 1 número, 1 caractere
 * especial. Fonte única para a checklist do cadastro (components/auth/
 * PasswordChecklist.tsx), a dica do login (components/auth/PasswordHint.tsx)
 * e o refine abaixo — mudar a regra num lugar só muda a UI inteira.
 */
export const PASSWORD_REQUIREMENTS: readonly PasswordRequirement[] = [
  { id: "length", label: "Ao menos 8 caracteres", test: (value) => value.length >= 8 },
  { id: "lowercase", label: "1 letra minúscula (a–z)", test: (value) => /[a-z]/.test(value) },
  { id: "uppercase", label: "1 letra maiúscula (A–Z)", test: (value) => /[A-Z]/.test(value) },
  { id: "digit", label: "1 número (0–9)", test: (value) => /\d/.test(value) },
  {
    id: "special",
    label: "1 caractere especial (ex.: ! @ # $ %)",
    test: (value) => /[^A-Za-z0-9\s]/.test(value),
  },
];

export function isPasswordCompliant(value: string): boolean {
  return PASSWORD_REQUIREMENTS.every((requirement) => requirement.test(value));
}

const passwordSchema = z
  .string()
  .min(8, "A senha precisa de ao menos 8 caracteres")
  .refine((value) => utf8ByteLength(value) <= 72, {
    message: "A senha deve ter no máximo 72 bytes em UTF-8 (acentos contam mais de 1 byte)",
  })
  .refine(isPasswordCompliant, {
    message: "A senha precisa atender a todos os requisitos listados abaixo",
  });

export const registerSchema = z
  .object({
    email: z
      .string()
      .min(5, "E-mail muito curto")
      .max(255)
      .trim()
      .toLowerCase()
      .refine((value) => EMAIL_PATTERN.test(value), { message: "E-mail inválido" }),
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Confirme a senha"),
    full_name: z.string().max(255).trim().optional().or(z.literal("")),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "As senhas não coincidem",
    path: ["confirmPassword"],
  });
export type RegisterInput = z.infer<typeof registerSchema>;

export const loginSchema = z.object({
  email: z.string().min(1, "Informe o e-mail").trim(),
  password: z.string().min(1, "Informe a senha"),
});
export type LoginInput = z.infer<typeof loginSchema>;

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Informe a senha atual"),
    new_password: passwordSchema,
    confirmNewPassword: z.string().min(1, "Confirme a nova senha"),
    // Sem `.default()` de propósito: com zod, `.default()` faz o tipo de
    // entrada divergir do de saída (`boolean | undefined` vs `boolean`), e o
    // `zodResolver` do react-hook-form exige os dois iguais. O valor padrão
    // vem do `defaultValues` do `useForm` em cada formulário.
    revoke_other_sessions: z.boolean(),
  })
  .refine((data) => data.current_password !== data.new_password, {
    message: "A nova senha deve ser diferente da atual",
    path: ["new_password"],
  })
  .refine((data) => data.new_password === data.confirmNewPassword, {
    message: "As senhas não coincidem",
    path: ["confirmNewPassword"],
  });
export type ChangePasswordInput = z.infer<typeof changePasswordSchema>;

export const profileUpdateSchema = z.object({
  full_name: z.string().max(255).trim().optional().or(z.literal("")),
});
export type ProfileUpdateInput = z.infer<typeof profileUpdateSchema>;
