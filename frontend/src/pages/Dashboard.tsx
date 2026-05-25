import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading } from "../components/Loading";
import { ConfigBanner } from "../components/ConfigBanner";

export default function Dashboard() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([api.dashboard(), api.health()])
      .then(([d, h]) => {
        setData(d);
        setHealth(h);
      })
      .catch((e) => setErr(e.message));
  }, []);

  if (err)
    return (
      <ConfigBanner
        type="error"
        message={`Backend unreachable: ${err}. Start API with: cd backend && uvicorn app.main:app --reload`}
      />
    );
  if (!data) return <Loading />;

  const metrics = [
    { label: "New opportunities", value: data.new_opportunities },
    { label: "Eligible", value: data.eligible_opportunities },
    { label: "Drafts ready", value: data.drafts_ready },
    { label: "Missing info", value: data.missing_info_requests },
    { label: "Needs review", value: data.applications_needs_review },
    { label: "Submitted (week)", value: data.submitted_this_week },
    { label: "Won", value: data.won_count },
  ];

  const deadlines = (data.upcoming_deadlines as { name: string; deadline: string }[]) || [];

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-1">Mission Control</h2>
      <p className="text-hive-muted text-sm mb-6">Your private scholarship command center</p>

      {health && !health.gemini_configured && (
        <ConfigBanner message="Gemini not configured — essay AI drafts disabled until GEMINI_API_KEY is set." />
      )}
      {health && !health.tavily_configured && (
        <ConfigBanner message="Tavily not configured — web scholarship search disabled until TAVILY_API_KEY is set." />
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {metrics.map((m) => (
          <div key={m.label} className="card">
            <p className="text-3xl font-bold text-hive-gold">{String(m.value)}</p>
            <p className="text-sm text-hive-muted mt-1">{m.label}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="font-semibold mb-3">Upcoming deadlines</h3>
          {deadlines.length === 0 ? (
            <p className="text-hive-muted text-sm">No upcoming deadlines — run Web Search or add scholarships.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {deadlines.map((d, i) => (
                <li key={i} className="flex justify-between border-b border-hive-border/50 pb-2">
                  <span>{d.name}</span>
                  <span className="text-hive-gold">{d.deadline}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card">
          <h3 className="font-semibold mb-3">Quick actions</h3>
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary text-sm" onClick={() => api.jobs.recalculate()}>
              Recalculate eligibility
            </button>
            <button className="btn-secondary text-sm" onClick={() => api.webSearch.run()}>
              Run Web Search
            </button>
            <button className="btn-secondary text-sm" onClick={() => api.jobs.scanGmail()}>
              Scan Gmail now
            </button>
          </div>
          <p className="text-xs text-hive-muted mt-4">
            Background scheduling is stubbed — use manual triggers for MVP.
          </p>
        </div>
      </div>
    </div>
  );
}
