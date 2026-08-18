"use client";

import { Download, FileText } from "lucide-react";
import { useState } from "react";

import { exportTransactions, type ExportFormat } from "@/lib/api/transactions";
import { describeError } from "@/lib/errors";
import { useToast } from "@/lib/toast";
import { Button } from "@/components/ui/Button";

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

const CONFIRM_MESSAGE =
  "A exportação traz todas as transações do período, ignorando os filtros de tipo, categoria e busca aplicados na tela (GET /transactions/export só aceita formato e período). Continuar?";

/**
 * "Exportar período", nunca "Exportar resultados" (plan, Fase 3): o back-end
 * não filtra a exportação por tipo/categoria/busca, só por período. Blob via
 * axios porque é rota autenticada — `<a href>` simples não carrega o cookie
 * de sessão do jeito que o BFF precisa.
 */
export function ExportButton({
  start,
  end,
  hasActiveFilters,
}: {
  start: string;
  end: string;
  hasActiveFilters: boolean;
}) {
  const toast = useToast();
  const [pending, setPending] = useState<ExportFormat | null>(null);

  async function handleExport(format: ExportFormat) {
    if (hasActiveFilters && !window.confirm(CONFIRM_MESSAGE)) {
      return;
    }
    setPending(format);
    try {
      const { blob, filename } = await exportTransactions({ format, start, end });
      downloadBlob(blob, filename);
    } catch (error) {
      toast.show({
        variant: "error",
        title: "Não foi possível exportar",
        description: describeError(error).message,
      });
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="flex gap-2">
      <Button
        type="button"
        variant="secondary"
        loading={pending === "csv"}
        disabled={pending !== null}
        onClick={() => handleExport("csv")}
      >
        <Download className="h-4 w-4" aria-hidden="true" />
        Exportar período (CSV)
      </Button>
      <Button
        type="button"
        variant="secondary"
        loading={pending === "pdf"}
        disabled={pending !== null}
        onClick={() => handleExport("pdf")}
      >
        <FileText className="h-4 w-4" aria-hidden="true" />
        PDF
      </Button>
    </div>
  );
}
