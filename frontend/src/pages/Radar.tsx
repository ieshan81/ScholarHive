import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading, EmptyState } from "../components/Loading";
import { StatusBadge } from "../components/StatusBadge";

type Sch = {
  id: number;
  name: string;
  award_amount?: string;
  deadline?: string;
  status: string;
  eligibility_score: number;
  effort_score: number;
  essay_required: boolean;
  is_demo?: boolean;
};

const FILTERS = [
  { key: "", label: "All" },
  { key: "eligible", label: "Eligible" },
  { key: "maybe_eligible", label: "Maybe eligible" },
  { key: "not_eligible", label: "Not eligible" },
  { key: "deadline_soon", label: "Deadline soon" },
  { key: "mechanical_engineering", label: "Mechanical eng." },
  { key: "international_students", label: "International" },
  { key: "no_essay", label: "No essay" },
  { key: "high_award", label: "High award" },
  { key: "low_effort", label: "Low effort" },
];

export default function Radar() {
  const [items, setItems] = useState<Sch[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const load = (f?: string) => {
    setLoading(true);
    api.scholarships
      .list(f || undefined)
      .then((d) => setItems(d as Sch[]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load(filter);
  }, [filter]);

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-6">Scholarship Radar</h2>
      <div className="flex flex-wrap gap-2 mb-6">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`text-sm px-3 py-1 rounded-full border ${
              filter === f.key ? "border-hive-gold text-hive-gold" : "border-hive-border text-hive-muted"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>
      {loading ? (
        <Loading />
      ) : items.length === 0 ? (
        <EmptyState title="No scholarships match this filter" hint="Add opportunities or run Gmail scan" />
      ) : (
        <div className="grid gap-4">
          {items.map((s) => (
            <div key={s.id} className="card flex flex-wrap justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">{s.name}</h3>
                  {s.is_demo && <span className="badge bg-purple-500/20 text-purple-300">demo</span>}
                </div>
                <p className="text-sm text-hive-muted mt-1">
                  {s.award_amount || "Amount TBD"} · Deadline: {s.deadline || "—"}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm">Eligibility: {s.eligibility_score}%</span>
                <span className="text-sm text-hive-muted">Effort: {s.effort_score}</span>
                <StatusBadge status={s.status} />
                <button
                  className="btn-secondary text-sm"
                  onClick={() => api.scholarships.evaluate(s.id).then(() => load(filter))}
                >
                  Evaluate
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
