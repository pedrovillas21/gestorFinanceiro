"use client";

import { ChevronDown, KeyRound } from "lucide-react";
import { useState } from "react";

import { PASSWORD_REQUIREMENTS } from "@/lib/schemas/auth";

/**
 * Lembrete estático da regra de senha, para o login — deliberadamente sem o
 * comportamento "ao vivo" do PasswordChecklist do cadastro. O login não
 * valida complexidade (backend/app/schemas/auth.py: `LoginRequest` não tem o
 * validador), então marcar requisitos como atendidos/pendentes contra o que
 * foi digitado aqui seria inventar um erro que o servidor nunca reportaria.
 * Fica fechado por padrão — é referência para quem esqueceu a regra, não uma
 * validação, então não compete por atenção com os campos do formulário.
 */
export function PasswordHint() {
  const [open, setOpen] = useState(false);

  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        className="flex items-center gap-1.5 text-muted hover:text-surface-foreground"
      >
        <KeyRound className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>Quais eram as regras de senha da minha conta?</span>
        <ChevronDown
          className={`h-3.5 w-3.5 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>
      {open ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
          {PASSWORD_REQUIREMENTS.map((requirement) => (
            <li key={requirement.id}>{requirement.label}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
