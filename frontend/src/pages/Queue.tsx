import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading } from "../components/Loading";
import { StatusBadge } from "../components/StatusBadge";

const COLUMNS: { key: string; label: string }[] = [
  { key: "found", label: "New" },
  { key: "eligible", label: "Eligible" },
  { key: "missing_info", label: "Missing Info" },
  { key: "draft_ready", label: "Draft Ready" },
  { key: "needs_review", label: "Needs Review" },
  { key: "ready_to_apply", label: "Ready to Apply" },
  { key: "manual_step_needed", label: "Manual Step" },
  { key: "submitted", label: "Submitted" },
  { key: "rejected", label: "Rejected" },
  { key: "won", label: "Won" },
];

type Sch = {
  id: number;
  name: string;
  deadline?: string;
  award_amount?: string;
  next_action?: string;
  eligibility_score: number;
  effort_score: number;
  status: string;
};

export default function Queue() {
  const [items, setItems] = useState<Sch[]>([]);
  const [prep, setPrep] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () =>
    api.scholarships.list().then((d) => setItems(d as Sch[])).finally(() => setLoading(false));

  useEffect(() => {
    load();
  }, []);

  const move = (id: number, status: string) => {
    api.scholarships.moveStatus(id, status).then(load);
  };

  if (loading) return <Loading />;

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-6">Application Queue</h2>
      <p className="text-sm text-hive-muted mb-4">
        Human approval required · No auto-submission
      </p>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((col) => {
          const cards = items.filter((s) => s.status === col.key);
          return (
            <div
              key={col.key}
              className="min-w-[220px] flex-shrink-0 bg-hive-panel/50 rounded-xl border border-hive-border p-3"
            >
              <h3 className="text-sm font-semibold text-hive-gold mb-3">
                {col.label} ({cards.length})
              </h3>
              <div className="space-y-2">
                {cards.map((s) => (
                  <div key={s.id} className="card p-3 text-sm">
                    <p className="font-medium line-clamp-2">{s.name}</p>
                    <p className="text-hive-muted text-xs mt-1">{s.award_amount}</p>
                    <p className="text-xs mt-1">Score: {s.eligibility_score}%</p>
                    <span className="badge bg-amber-500/20 text-amber-200 text-[10px] mt-2 inline-block">
                      approval required
                    </span>
                    <div className="mt-2 flex flex-col gap-1">
                      <button
                        className="text-xs text-hive-accent"
                        onClick={() => api.scholarships.applyPrep(s.id).then(setPrep)}
                      >
                        Apply prep
                      </button>
                      <select
                        className="input-field text-xs py-1"
                        value={s.status}
                        onChange={(e) => move(s.id, e.target.value)}
                      >
                        {COLUMNS.map((c) => (
                          <option key={c.key} value={c.key}>
                            → {c.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {prep && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="card max-w-lg w-full max-h-[80vh] overflow-auto">
            <h3 className="text-lg font-semibold text-hive-gold">Apply Preparation</h3>
            <p className="text-sm text-hive-muted mt-1">{String(prep.scholarship_name)}</p>
            <ul className="mt-4 text-sm space-y-2">
              {(prep.warnings as string[])?.map((w, i) => (
                <li key={i} className="text-amber-300">⚠ {w}</li>
              ))}
            </ul>
            {prep.essay_final_text ? (
              <div className="mt-4 p-3 bg-hive-panel rounded text-xs max-h-32 overflow-auto">
                {String(prep.essay_final_text).slice(0, 500)}...
              </div>
            ) : null}
            {prep.source_url ? (
              <a
                href={String(prep.source_url)}
                target="_blank"
                rel="noreferrer"
                className="text-hive-accent text-sm mt-3 block"
              >
                Open portal (manual)
              </a>
            ) : null}
            <div className="flex gap-2 mt-6">
              <button className="btn-primary" onClick={() => setPrep(null)}>
                Close
              </button>
              <button
                className="btn-secondary"
                onClick={() => {
                  if (prep.scholarship_id)
                    api.scholarships
                      .moveStatus(Number(prep.scholarship_id), "submitted")
                      .then(() => {
                        setPrep(null);
                        load();
                      });
                }}
              >
                Mark as Submitted (manual)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
