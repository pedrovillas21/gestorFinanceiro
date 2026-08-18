export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-border/60 ${className}`} aria-hidden="true" />;
}
