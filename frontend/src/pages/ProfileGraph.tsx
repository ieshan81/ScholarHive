import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading } from "../components/Loading";

export default function ProfileGraph() {
  const [clusters, setClusters] = useState<Record<string, unknown[]>>({});
  const [paste, setPaste] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => api.profileGraph.list().then((d) => {
    setClusters((d as { clusters: Record<string, unknown[]> }).clusters || {});
    setLoading(false);
  });

  useEffect(() => {
    load();
  }, []);

  if (loading) return <Loading />;

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-6">Profile Graph</h2>
      <div className="card mb-6 max-w-2xl">
        <p className="text-sm text-hive-muted mb-2">Paste essay, resume text, or notes — creates knowledge nodes (no OCR in MVP).</p>
        <textarea className="input-field h-32" value={paste} onChange={(e) => setPaste(e.target.value)} />
        <button
          className="btn-primary mt-2"
          onClick={() => api.profileGraph.extractText(paste).then(() => { setPaste(""); load(); })}
        >
          Extract to graph
        </button>
      </div>
      {Object.entries(clusters).map(([type, nodes]) => (
        <div key={type} className="mb-6">
          <h3 className="text-hive-gold font-semibold capitalize mb-2">{type.replace(/_/g, " ")}</h3>
          <div className="grid md:grid-cols-2 gap-3">
            {(nodes as { id: number; title: string; summary?: string; approved_by_user: boolean }[]).map((n) => (
              <div key={n.id} className="card p-3">
                <p className="font-medium text-sm">{n.title}</p>
                <p className="text-xs text-hive-muted line-clamp-3 mt-1">{n.summary}</p>
                <button className="text-xs text-hive-accent mt-2" onClick={() => api.profileGraph.approve(n.id).then(load)}>
                  {n.approved_by_user ? "Approved" : "Approve"}
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
