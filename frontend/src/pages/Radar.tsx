import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Loading, EmptyState } from "../components/Loading";
import { StatusBadge } from "../components/StatusBadge";

type Sch = {
  id: number;
  name: string;
  source_type?: string;
  source_url?: string;
  application_url?: string;
  award_amount?: string;
  deadline?: string;
  status: string;
  eligibility_score: number;
  effort_score: number;
  trust_score?: number;
  extraction_confidence?: number;
  essay_required: boolean;
  manual_step_likely?: boolean;
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

function sourceBadge(type?: string) {
  const t = type || "manual";
  const colors: Record<string, string> = {
    web: "bg-blue-500/20 text-blue-300",
    gmail: "bg-red-500/20 text-red-300",
    manual: "bg-slate-500/20 text-slate-300",
  };
  return <span className={`badge ${colors[t] || colors.manual}`}>{t}</span>;
}

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
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-display text-hive-gold">Scholarship Radar</h2>
        <Link to="/web-search" className="btn-secondary text-sm">
          Run Web Search
        </Link>
      </div>
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
        <EmptyState
          title="No scholarships found yet"
          hint="Run Web Search, connect Gmail, or add a scholarship manually."
        />
      ) : (
        <div className="grid gap-4">
          {items.map((s) => (
            <div key={s.id} className="card flex flex-wrap justify-between gap-4">
              <div className="flex-1 min-w-[240px]">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold">{s.name}</h3>
                  {sourceBadge(s.source_type)}
                  {s.manual_step_likely && (
                    <span className="badge bg-orange-500/20 text-orange-300">manual step</span>
                  )}
                </div>
                <p className="text-sm text-hive-muted mt-1">
                  {s.award_amount || "Amount TBD"} · Deadline: {s.deadline || "—"}
                </p>
                <p className="text-xs text-hive-muted mt-1">
                  Trust: {s.trust_score ?? "—"} · Confidence: {s.extraction_confidence ?? "—"}%
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm">Eligibility: {s.eligibility_score}%</span>
                <span className="text-sm text-hive-muted">Effort: {s.effort_score}</span>
                <StatusBadge status={s.status} />
                <button
                  className="btn-secondary text-sm"
                  onClick={() => api.scholarships.evaluate(s.id).then(() => load(filter))}
                >
                  Evaluate
                </button>
                {s.essay_required && (
                  <button
                    className="btn-secondary text-sm"
                    onClick={() => api.essays.generate(s.id).catch((e) => alert(e.message))}
                  >
                    Generate Draft
                  </button>
                )}
                {(s.application_url || s.source_url) && (
                  <a
                    href={s.application_url || s.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary text-sm"
                  >
                    Open Source
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
