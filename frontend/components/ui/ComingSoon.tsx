import type { LucideIcon } from "lucide-react";
import { Construction } from "lucide-react";

import { EmptyState } from "@/components/ui/EmptyState";

/** Placeholder das telas ainda não construídas — o shell (Fase 2) já roteia para elas. */
export function ComingSoon({
  title,
  description,
  icon = Construction,
}: {
  title: string;
  description: string;
  icon?: LucideIcon;
}) {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-lg font-semibold text-foreground">{title}</h1>
      <EmptyState icon={icon} title="Em construção" description={description} />
    </div>
  );
}
