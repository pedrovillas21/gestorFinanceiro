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

const passwordSchema = z
  .string()
  .min(8, "A senha precisa de ao menos 8 caracteres")
  .refine((value) => utf8ByteLength(value) <= 72, {
    message: "A senha deve ter no máximo 72 bytes em UTF-8 (acentos contam mais de 1 byte)",
  });

export const registerSchema = z.object({
  email: z
    .string()
    .min(5, "E-mail muito curto")
    .max(255)
    .trim()
    .toLowerCase()
    .refine((value) => EMAIL_PATTERN.test(value), { message: "E-mail inválido" }),
  password: passwordSchema,
  full_name: z.string().max(255).trim().optional().or(z.literal("")),
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
    revoke_other_sessions: z.boolean().default(true),
  })
  .refine((data) => data.current_password !== data.new_password, {
    message: "A nova senha deve ser diferente da atual",
    path: ["new_password"],
  });
export type ChangePasswordInput = z.infer<typeof changePasswordSchema>;

export const profileUpdateSchema = z.object({
  full_name: z.string().max(255).trim().optional().or(z.literal("")),
});
export type ProfileUpdateInput = z.infer<typeof profileUpdateSchema>;
