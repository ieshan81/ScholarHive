const STATUS_COLORS: Record<string, string> = {
  eligible: "bg-emerald-500/20 text-emerald-300",
  maybe_eligible: "bg-amber-500/20 text-amber-300",
  not_eligible: "bg-red-500/20 text-red-300",
  found: "bg-slate-500/20 text-slate-300",
  draft_ready: "bg-blue-500/20 text-blue-300",
  needs_review: "bg-purple-500/20 text-purple-300",
  ready_to_apply: "bg-hive-gold/20 text-hive-gold",
  manual_step_needed: "bg-orange-500/20 text-orange-300",
  submitted: "bg-cyan-500/20 text-cyan-300",
  won: "bg-emerald-400/30 text-emerald-200",
  rejected: "bg-red-500/20 text-red-400",
  missing_info: "bg-amber-500/20 text-amber-200",
  pending: "bg-amber-500/20 text-amber-200",
  approved: "bg-emerald-500/20 text-emerald-300",
  draft: "bg-slate-500/20 text-slate-300",
};

export function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] || "bg-slate-600/30 text-slate-300";
  return (
    <span className={`badge ${cls}`}>{status.replace(/_/g, " ")}</span>
  );
}
