import type { ButtonHTMLAttributes } from "react";

import { Spinner } from "@/components/ui/Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
  fullWidth?: boolean;
}

const VARIANT_CLASS: Record<Variant, string> = {
  primary: "bg-primary text-primary-foreground hover:opacity-90",
  secondary: "bg-surface text-surface-foreground border border-border hover:bg-border/40",
  ghost: "text-surface-foreground hover:bg-surface",
  danger: "bg-danger text-white hover:opacity-90",
};

export function Button({
  variant = "primary",
  loading = false,
  fullWidth = false,
  disabled,
  className = "",
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${VARIANT_CLASS[variant]} ${fullWidth ? "w-full" : ""} ${className}`}
    >
      {loading ? <Spinner /> : null}
      {children}
    </button>
  );
}
