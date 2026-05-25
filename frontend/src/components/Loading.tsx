export function Loading() {
  return (
    <div className="flex items-center justify-center py-16 text-hive-muted">
      <div className="animate-pulse">Loading...</div>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="card text-center py-12 text-hive-muted">
      <p className="text-lg text-slate-300">{title}</p>
      {hint && <p className="text-sm mt-2">{hint}</p>}
    </div>
  );
}
