"use client";

import { X } from "lucide-react";
import { useEffect, type ReactNode } from "react";

/**
 * Diálogo genérico reutilizado pelo formulário de transação, pela confirmação
 * de exclusão e pelo aviso de exportação (components/transactions/*). Fecha
 * com Esc ou clique no fundo; `open={false}` desmonta o conteúdo, então
 * formulários dentro dele não guardam estado de uma abertura para a outra.
 */
export function Modal({
  open,
  onClose,
  title,
  children,
  widthClassName = "max-w-md",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  widthClassName?: string;
}) {
  useEffect(() => {
    if (!open) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button type="button" aria-label="Fechar" onClick={onClose} className="absolute inset-0 bg-black/50" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`relative z-10 max-h-[90vh] w-full ${widthClassName} overflow-y-auto rounded-lg border border-border bg-surface p-4 shadow-xl`}
      >
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="text-sm font-semibold text-surface-foreground">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="shrink-0 rounded p-1 text-muted hover:bg-border/40 hover:text-surface-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
