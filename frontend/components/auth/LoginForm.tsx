"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { login, readRetryAfterSeconds } from "@/lib/api/auth";
import { describeError } from "@/lib/errors";
import { loginSchema, type LoginInput } from "@/lib/schemas/auth";
import { PasswordHint } from "@/components/auth/PasswordHint";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { PasswordField } from "@/components/ui/PasswordField";
import { TextField } from "@/components/ui/TextField";

export function LoginForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const [retryAfter, setRetryAfter] = useState<number | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  // Contagem regressiva do bloqueio progressivo (10 min → 3 h → 24 h). O
  // Retry-After chega em segundos direto do back-end via app/api/auth/login —
  // nada de backoff fixo chutado no front (plan, Fase 2).
  useEffect(() => {
    if (retryAfter === null || retryAfter <= 0) {
      return;
    }
    const timer = setInterval(() => {
      setRetryAfter((current) => (current === null ? null : Math.max(0, current - 1)));
    }, 1000);
    return () => clearInterval(timer);
  }, [retryAfter]);

  async function onSubmit(values: LoginInput) {
    setFormError(null);
    try {
      const { user } = await login(values);
      // Senha antiga fora da regra atual: barra o dashboard até trocar. Ver
      // app/trocar-senha/page.tsx e backend/app/models/user.py.
      router.push(user.must_change_password ? "/trocar-senha" : "/");
      router.refresh();
    } catch (error) {
      const retrySeconds = readRetryAfterSeconds(error);
      if (retrySeconds !== null) {
        setRetryAfter(retrySeconds);
        setFormError(`Muitas tentativas. Tente novamente em ${retrySeconds}s.`);
        return;
      }
      const status = (error as { response?: { status?: number } }).response?.status;
      if (status === 401) {
        // Nunca revela se o e-mail existe — vale também para bloqueio de
        // e-mail inexistente, de propósito (plan, Fase 2).
        setFormError("E-mail ou senha inválidos.");
        return;
      }
      setFormError(describeError(error).message);
    }
  }

  const blocked = retryAfter !== null && retryAfter > 0;

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      {formError ? (
        <Alert variant="error">
          {formError}
          {blocked ? (
            <span className="mt-1 block font-medium tabular-nums">
              Aguarde {retryAfter}s antes de tentar de novo.
            </span>
          ) : null}
        </Alert>
      ) : null}

      <TextField
        label="E-mail"
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...register("email")}
      />

      <PasswordField
        label="Senha"
        autoComplete="current-password"
        error={errors.password?.message}
        below={<PasswordHint />}
        {...register("password")}
      />

      <Button type="submit" loading={isSubmitting} disabled={blocked} fullWidth>
        {blocked ? `Aguarde ${retryAfter}s` : "Entrar"}
      </Button>
    </form>
  );
}
