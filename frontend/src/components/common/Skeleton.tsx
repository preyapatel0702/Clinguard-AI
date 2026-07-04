interface SkeletonProps {
  className?: string;
}

/** Base shimmer block. Compose with width/height utility classes. */
export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={`block animate-pulse rounded-md bg-gray-200 dark:bg-white/10 ${className}`}
    />
  );
}

/** A row of skeleton text lines, e.g. for card summaries. */
export function SkeletonText({
  lines = 3,
  className = "",
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-2 ${className}`} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={`h-3 ${i === lines - 1 ? "w-2/3" : "w-full"}`}
        />
      ))}
    </div>
  );
}

/** Skeleton placeholder shaped like a KPI/summary card. */
export function SkeletonCard({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] ${className}`}
      aria-hidden="true"
    >
      <Skeleton className="mb-4 h-4 w-24" />
      <Skeleton className="mb-2 h-7 w-20" />
      <Skeleton className="h-3 w-32" />
    </div>
  );
}

/** Skeleton placeholder for a data table. */
export function SkeletonTable({
  rows = 5,
  columns = 4,
  className = "",
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={`w-full ${className}`} aria-hidden="true">
      {Array.from({ length: rows }).map((_, r) => (
        <div
          key={r}
          className="flex items-center gap-4 border-b border-gray-100 py-3 last:border-b-0 dark:border-gray-800"
        >
          {Array.from({ length: columns }).map((_, c) => (
            <Skeleton
              key={c}
              className={`h-3.5 ${c === 0 ? "w-1/4" : "flex-1"}`}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
