"use client";

import { Check, Circle } from "lucide-react";

import { PASSWORD_REQUIREMENTS } from "@/lib/schemas/auth";

/**
 * Checklist ao vivo do cadastro — cada requisito acende conforme o usuário
 * digita. Faz sentido só aqui: é o único momento em que o front conhece a
 * senha em texto puro e pode validá-la contra a regra nova. No login (ver
 * PasswordHint) a mesma lista existe, mas sem reagir ao campo — uma senha
 * antiga pode ser válida sem cumprir requisitos que não existiam quando foi
 * criada, então "acender" a checklist ali seria mostrar um erro que não é um.
 */
export function PasswordChecklist({ password }: { password: string }) {
  const metCount = PASSWORD_REQUIREMENTS.filter((requirement) => requirement.test(password)).length;
  const total = PASSWORD_REQUIREMENTS.length;
  const allMet = metCount === total;

  return (
    <div
      className={`rounded-md border p-3 transition-colors ${allMet ? "border-success/40 bg-success/5" : "border-border bg-surface"}`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-muted">Requisitos da senha</p>
        <p className={`text-xs font-medium ${allMet ? "text-success" : "text-muted"}`}>
          {metCount}/{total}
        </p>
      </div>
      <div className="mb-2 h-1 overflow-hidden rounded-full bg-border">
        <div
          className={`h-full rounded-full transition-all ${allMet ? "bg-success" : "bg-primary"}`}
          style={{ width: `${(metCount / total) * 100}%` }}
        />
      </div>
      <ul aria-live="polite" className="space-y-1">
        {PASSWORD_REQUIREMENTS.map((requirement) => {
          const met = requirement.test(password);
          return (
            <li
              key={requirement.id}
              className={`flex items-center gap-2 text-xs transition-colors ${met ? "text-success" : "text-muted"}`}
            >
              {met ? (
                <Check className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              ) : (
                <Circle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              )}
              <span>{requirement.label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
