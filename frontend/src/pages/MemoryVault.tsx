import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading } from "../components/Loading";
import { ConfigBanner } from "../components/ConfigBanner";

type Tab = "overview" | "uploads" | "map" | "conflicts" | "approved" | "sources";

type Cluster = {
  count: number;
  auto_approved: number;
  needs_review: number;
  conflicts: number;
  nodes: Array<{
    id: number;
    title: string;
    summary?: string;
    status: string;
    confidence: number;
    source_excerpt?: string;
    node_type: string;
  }>;
};

export default function MemoryVault() {
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<Record<string, unknown> | null>(null);
  const [clusters, setClusters] = useState<Record<string, Cluster>>({});
  const [conflicts, setConflicts] = useState<unknown[]>([]);
  const [paste, setPaste] = useState("");
  const [pasteTitle, setPasteTitle] = useState("Pasted essay");
  const [sourceType, setSourceType] = useState("essay");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedCluster, setSelectedCluster] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([api.memoryVault.overview(), api.memoryVault.conflicts()])
      .then(([o, c]) => {
        setOverview(o);
        setClusters((o.clusters as Record<string, Cluster>) || {});
        setConflicts(c as unknown[]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handlePaste = async () => {
    setMsg("Processing…");
    try {
      const r = await api.memoryVault.paste(paste, pasteTitle, sourceType);
      setMsg(`Done — ${JSON.stringify((r as Record<string, unknown>).memory || r)}`);
      load();
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Paste failed");
    }
  };

  const handleUpload = async (file: File | null) => {
    if (!file) return;
    setMsg("Uploading…");
    try {
      const r = await api.memoryVault.upload(file, sourceType);
      setMsg(JSON.stringify(r));
      load();
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Upload failed");
    }
  };

  const storageWarning = (overview?.storage as Record<string, unknown>)?.warning as string | undefined;

  if (loading) return <Loading />;

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "uploads", label: "Uploads" },
    { id: "map", label: "Memory Map" },
    { id: "conflicts", label: "Conflicts" },
    { id: "approved", label: "Approved Facts" },
    { id: "sources", label: "Source Documents" },
  ];

  const approvedNodes = Object.values(clusters).flatMap((c) =>
    c.nodes.filter((n) => n.status === "auto_approved" || n.status === "user_confirmed")
  );
  const reviewNodes = Object.values(clusters).flatMap((c) =>
    c.nodes.filter((n) => n.status === "needs_review")
  );

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-2">Ieshan Memory Vault</h2>
      <p className="text-sm text-hive-muted mb-4">
        Upload essays, resume, and notes once. AI extracts facts and stories — you only review conflicts and uncertain items.
      </p>
      {storageWarning && <ConfigBanner message={storageWarning} />}

      <div className="flex flex-wrap gap-2 mb-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "btn-primary text-sm" : "btn-secondary text-sm"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
        <button className="btn-secondary text-sm ml-auto" onClick={() => api.memoryVault.bulkApprove().then(load)}>
          Approve all high confidence
        </button>
        <button className="btn-secondary text-sm" onClick={() => api.memoryVault.syncLegacy().then(load)}>
          Import Story Bank
        </button>
      </div>

      {msg && <p className="text-sm mb-4 p-2 rounded bg-hive-panel">{msg}</p>}

      {tab === "overview" && (
        <div className="grid md:grid-cols-3 gap-4">
          <div className="card">
            <p className="text-2xl font-bold text-hive-gold">{String(overview?.total_nodes || 0)}</p>
            <p className="text-sm text-hive-muted">Memory nodes</p>
          </div>
          <div className="card">
            <p className="text-2xl font-bold">{approvedNodes.length}</p>
            <p className="text-sm text-hive-muted">Auto-approved / confirmed</p>
          </div>
          <div className="card">
            <p className="text-2xl font-bold">{reviewNodes.length}</p>
            <p className="text-sm text-hive-muted">Needs your review</p>
          </div>
        </div>
      )}

      {tab === "uploads" && (
        <div className="card max-w-2xl space-y-4">
          <div>
            <label className="text-sm text-hive-muted">Source type</label>
            <select className="input-field mt-1" value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
              <option value="essay">Essay</option>
              <option value="resume">Resume</option>
              <option value="personal_statement">Personal statement</option>
              <option value="notes">Notes</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="text-sm text-hive-muted">Upload PDF / TXT / DOCX</label>
            <input
              type="file"
              accept=".pdf,.txt,.docx,.md"
              className="input-field mt-1"
              onChange={(e) => handleUpload(e.target.files?.[0] || null)}
            />
          </div>
          <div>
            <input className="input-field mb-2" value={pasteTitle} onChange={(e) => setPasteTitle(e.target.value)} placeholder="Title" />
            <textarea
              className="input-field min-h-[160px]"
              value={paste}
              onChange={(e) => setPaste(e.target.value)}
              placeholder="Paste essay, resume text, or notes…"
            />
            <button className="btn-primary mt-2" onClick={handlePaste}>
              Extract memories from paste
            </button>
          </div>
        </div>
      )}

      {tab === "map" && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(clusters).map(([name, c]) => (
            <button
              key={name}
              className="card text-left hover:border-hive-gold/40"
              onClick={() => setSelectedCluster(selectedCluster === name ? null : name)}
            >
              <h3 className="font-semibold text-hive-gold">{name}</h3>
              <p className="text-xs text-hive-muted mt-1">
                {c.count} items · {c.auto_approved} approved · {c.needs_review} review · {c.conflicts} conflicts
              </p>
              {selectedCluster === name && (
                <ul className="mt-3 space-y-2 max-h-64 overflow-auto">
                  {c.nodes.map((n) => (
                    <li key={n.id} className="text-sm border-t border-hive-border pt-2">
                      <span className="text-xs text-hive-muted">{n.status}</span>
                      <p className="font-medium">{n.title}</p>
                      <p className="text-hive-muted line-clamp-2">{n.summary}</p>
                      <div className="flex gap-2 mt-1">
                        <button className="text-xs text-hive-gold" onClick={() => api.memoryVault.confirm(n.id).then(load)}>
                          Confirm
                        </button>
                        <button className="text-xs text-red-400" onClick={() => api.memoryVault.reject(n.id).then(load)}>
                          Reject
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </button>
          ))}
        </div>
      )}

      {tab === "conflicts" && (
        <div className="space-y-3">
          {conflicts.length === 0 ? (
            <p className="text-sm text-hive-muted">No conflicts detected.</p>
          ) : (
            (conflicts as Array<{ id: number; title: string; conflict_flag: string }>).map((c) => (
              <div key={c.id} className="card">
                <p className="font-medium">{c.title}</p>
                <p className="text-sm text-amber-300 mt-1">{c.conflict_flag}</p>
                <button className="btn-secondary text-sm mt-2" onClick={() => api.memoryVault.confirm(c.id).then(load)}>
                  Resolve — keep this version
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "approved" && (
        <div className="space-y-2">
          {approvedNodes.map((n) => (
            <div key={n.id} className="card p-3">
              <p className="font-medium">{n.title}</p>
              <p className="text-sm text-hive-muted">{n.summary}</p>
            </div>
          ))}
        </div>
      )}

      {tab === "sources" && (
        <div className="space-y-2">
          {((overview?.documents as Array<{ id: number; file_name: string; processing_status: string }>) || []).map((d) => (
            <div key={d.id} className="card p-3 flex justify-between">
              <span>{d.file_name}</span>
              <span className="text-xs text-hive-muted">{d.processing_status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
