import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading, EmptyState } from "../components/Loading";

type Portal = {
  id: number;
  domain: string;
  portal_name?: string;
  portal_url?: string;
  source_count: number;
  session_status: string;
  opportunities_discovered: number;
  checkpoints_pending: number;
};

export default function Portals() {
  const [portals, setPortals] = useState<Portal[]>([]);
  const [agent, setAgent] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.portals.list(), api.portals.agentStatus()]).then(([p, a]) => {
      setPortals(p as Portal[]);
      setAgent(a as Record<string, unknown>);
      setLoading(false);
    });
  }, []);

  if (loading) return <Loading />;

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-2">Portal Registry</h2>
      <p className="text-sm text-hive-muted mb-6">{String(agent.message)}</p>
      {portals.length === 0 ? (
        <EmptyState title="No portals yet" hint="Run Web Search or Gmail scan — domains are grouped automatically." />
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {portals.map((p) => (
            <div key={p.id} className="card">
              <h3 className="font-semibold">{p.portal_name || p.domain}</h3>
              <p className="text-xs text-hive-muted">{p.domain} · {p.source_count} sources</p>
              <p className="text-sm mt-2">Session: {p.session_status} · Opportunities: {p.opportunities_discovered}</p>
              <div className="flex gap-2 mt-4">
                {p.portal_url && (
                  <a href={p.portal_url} target="_blank" rel="noreferrer" className="btn-secondary text-sm">
                    Open portal
                  </a>
                )}
                <button
                  className="btn-primary text-sm"
                  onClick={() => api.portals.openSession(p.id).then((r) => alert(String((r as Record<string, unknown>).message)))}
                >
                  Connect / checkpoint
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
