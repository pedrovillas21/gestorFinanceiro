"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { isConflict, register as registerUser } from "@/lib/api/auth";
import { describeError } from "@/lib/errors";
import { registerSchema, type RegisterInput } from "@/lib/schemas/auth";
import { PasswordChecklist } from "@/components/auth/PasswordChecklist";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { PasswordField } from "@/components/ui/PasswordField";
import { TextField } from "@/components/ui/TextField";

export function RegisterForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: "", password: "", confirmPassword: "", full_name: "" },
  });

  const password = watch("password");

  async function onSubmit(values: RegisterInput) {
    setFormError(null);
    try {
      await registerUser({
        email: values.email,
        password: values.password,
        full_name: values.full_name || undefined,
      });
      // Entra direto no dashboard, sem passar pelo login (plan, Fase 2).
      router.push("/");
      router.refresh();
    } catch (error) {
      if (isConflict(error)) {
        setError("email", { message: "E-mail já cadastrado" });
        return;
      }
      setFormError(describeError(error).message);
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      {formError ? <Alert variant="error">{formError}</Alert> : null}

      <TextField
        label="Nome (opcional)"
        autoComplete="name"
        error={errors.full_name?.message}
        {...register("full_name")}
      />

      <TextField
        label="E-mail"
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...register("email")}
      />

      <PasswordField
        label="Senha"
        autoComplete="new-password"
        error={errors.password?.message}
        below={<PasswordChecklist password={password} />}
        {...register("password")}
      />

      <PasswordField
        label="Confirmar senha"
        autoComplete="new-password"
        error={errors.confirmPassword?.message}
        {...register("confirmPassword")}
      />

      <Button type="submit" loading={isSubmitting} fullWidth>
        Criar conta
      </Button>
    </form>
  );
}
