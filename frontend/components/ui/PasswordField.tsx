"use client";

import { Eye, EyeOff } from "lucide-react";
import { forwardRef, useId, useState, type InputHTMLAttributes, type ReactNode } from "react";

export interface PasswordFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
  error?: string;
  /** Conteúdo extra sob o campo — a checklist do cadastro ou a dica do login. */
  below?: ReactNode;
}

export const PasswordField = forwardRef<HTMLInputElement, PasswordFieldProps>(function PasswordField(
  { label, error, below, id, className = "", ...rest },
  ref,
) {
  const [visible, setVisible] = useState(false);
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const errorId = error ? `${inputId}-error` : undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-sm font-medium text-surface-foreground">
        {label}
      </label>
      <div className="relative">
        <input
          {...rest}
          ref={ref}
          id={inputId}
          type={visible ? "text" : "password"}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId}
          className={`w-full rounded-md border bg-background px-3 py-2 pr-10 text-sm text-foreground outline-none transition-colors placeholder:text-muted focus:border-primary ${error ? "border-danger" : "border-border"} ${className}`}
        />
        <button
          type="button"
          onClick={() => setVisible((current) => !current)}
          tabIndex={-1}
          className="absolute inset-y-0 right-0 flex items-center px-3 text-muted hover:text-surface-foreground"
          aria-label={visible ? "Ocultar senha" : "Mostrar senha"}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {error ? (
        <p id={errorId} role="alert" className="text-xs text-danger">
          {error}
        </p>
      ) : null}
      {below}
    </div>
  );
});
