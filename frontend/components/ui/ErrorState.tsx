import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/Button";

export function ErrorState({
  title = "Não foi possível carregar os dados",
  description,
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-danger/40 px-6 py-12 text-center">
      <AlertTriangle className="h-8 w-8 text-danger" aria-hidden="true" />
      <div className="space-y-1">
        <p className="text-sm font-medium text-surface-foreground">{title}</p>
        {description ? <p className="text-sm text-muted">{description}</p> : null}
      </div>
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry}>
          Tentar novamente
        </Button>
      ) : null}
    </div>
  );
}
