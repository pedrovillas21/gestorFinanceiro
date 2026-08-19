"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { changePassword, isUnauthorized } from "@/lib/api/auth";
import { describeError } from "@/lib/errors";
import { changePasswordSchema, type ChangePasswordInput } from "@/lib/schemas/auth";
import { PasswordChecklist } from "@/components/auth/PasswordChecklist";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { PasswordField } from "@/components/ui/PasswordField";

/**
 * Formulário de `/trocar-senha` — a mesma checklist ao vivo do cadastro
 * (components/auth/PasswordChecklist.tsx), porque aqui também é uma senha
 * nova sendo digitada pela primeira vez, não uma senha existente sendo
 * lembrada (ao contrário do login, que só mostra a dica estática).
 */
export function ForcePasswordChangeForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordInput>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      current_password: "",
      new_password: "",
      confirmNewPassword: "",
      revoke_other_sessions: true,
    },
  });

  const newPassword = watch("new_password");

  async function onSubmit(values: ChangePasswordInput) {
    setFormError(null);
    try {
      await changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
        revoke_other_sessions: values.revoke_other_sessions,
      });
      router.push("/");
      router.refresh();
    } catch (error) {
      if (isUnauthorized(error)) {
        setError("current_password", { message: "Senha atual incorreta" });
        return;
      }
      setFormError(describeError(error).message);
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      {formError ? <Alert variant="error">{formError}</Alert> : null}

      <PasswordField
        label="Senha atual"
        autoComplete="current-password"
        error={errors.current_password?.message}
        {...register("current_password")}
      />

      <PasswordField
        label="Nova senha"
        autoComplete="new-password"
        error={errors.new_password?.message}
        below={<PasswordChecklist password={newPassword} />}
        {...register("new_password")}
      />

      <PasswordField
        label="Confirmar nova senha"
        autoComplete="new-password"
        error={errors.confirmNewPassword?.message}
        {...register("confirmNewPassword")}
      />

      <Button type="submit" loading={isSubmitting} fullWidth>
        Atualizar senha e continuar
      </Button>
    </form>
  );
}
