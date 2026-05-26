import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading, EmptyState } from "../components/Loading";
import { ConfigBanner } from "../components/ConfigBanner";

type Portal = {
  id: number;
  domain: string;
  canonical_domain?: string;
  portal_name?: string;
  portal_url?: string;
  source_count: number;
  session_status: string;
  opportunities_discovered: number;
  checkpoints_pending: number;
  playwright_available?: boolean;
};

type AgentStatus = {
  browser_agent?: string;
  playwright_available?: boolean;
  chromium_available?: boolean;
  storage_writable?: boolean;
  mode?: string;
  message?: string;
  last_error?: string;
  safe_limits?: string[];
};

type RunState = {
  id: number;
  status: string;
  current_url?: string;
  opportunities_found?: number;
  errors?: string;
  checkpoint?: { type: string; instruction: string; status: string };
};

type Opportunity = {
  id: number;
  title: string;
  portal_url?: string;
  application_url?: string;
  deadline?: string;
  award_amount?: string;
};

export default function Portals() {
  const [portals, setPortals] = useState<Portal[]>([]);
  const [agent, setAgent] = useState<AgentStatus>({});
  const [showTracking, setShowTracking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activeRun, setActiveRun] = useState<RunState | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [message, setMessage] = useState("");
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([api.portals.list(showTracking), api.portals.agentStatus()]).then(([p, a]) => {
      setPortals(p as Portal[]);
      setAgent(a as AgentStatus);
      setLoading(false);
    });
  };

  useEffect(() => {
    load();
  }, [showTracking]);

  const selectPortal = async (id: number) => {
    setSelectedId(id);
    setActiveRun(null);
    setScreenshotUrl(null);
    const opps = await api.portals.opportunities(id);
    setOpportunities(opps as Opportunity[]);
  };

  const runAction = async (label: string, fn: () => Promise<Record<string, unknown>>) => {
    setMessage(`${label}…`);
    try {
      const r = await fn();
      setMessage(String(r.message || JSON.stringify(r)));
      if (r.run_id || r.portal_run_id) {
        const runId = Number(r.run_id || r.portal_run_id);
        const run = await api.portals.getRun(runId);
        setActiveRun(run as RunState);
        setScreenshotUrl(api.portals.screenshotUrl(runId));
      }
      if (selectedId) {
        const opps = await api.portals.opportunities(selectedId);
        setOpportunities(opps as Opportunity[]);
      }
      load();
    } catch (e: unknown) {
      setMessage(e instanceof Error ? e.message : "Action failed");
    }
  };

  if (loading) return <Loading />;

  const chromiumOk = !!agent.chromium_available;
  const selected = portals.find((p) => p.id === selectedId);

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-2">Portal Registry & Agent</h2>
      <p className="text-sm text-hive-muted mb-2">{agent.message}</p>
      <p className="text-xs text-hive-muted mb-4">
        Mode: {agent.mode} · Playwright: {chromiumOk ? "ready" : "unavailable"} · Storage:{" "}
        {agent.storage_writable ? "writable" : "limited"}
      </p>

      {!chromiumOk && (
        <ConfigBanner
          message={
            agent.last_error ||
            "Playwright/Chromium is not available. Check Railway build logs for playwright install chromium."
          }
        />
      )}

      {agent.safe_limits && (
        <ul className="text-xs text-hive-muted mb-4 list-disc pl-5">
          {agent.safe_limits.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      )}

      <label className="flex items-center gap-2 text-sm text-hive-muted mb-4">
        <input type="checkbox" checked={showTracking} onChange={(e) => setShowTracking(e.target.checked)} />
        Show ignored tracking domains
      </label>

      {message && <p className="text-sm mb-4 p-2 rounded bg-hive-panel">{message}</p>}

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="space-y-3">
          {portals.length === 0 ? (
            <EmptyState title="No portals" hint="Run Web Search or Gmail scan first." />
          ) : (
            portals.map((p) => (
              <button
                key={p.id}
                onClick={() => selectPortal(p.id)}
                className={`card w-full text-left ${selectedId === p.id ? "border-hive-gold/50" : ""}`}
              >
                <h3 className="font-semibold">{p.portal_name || p.domain}</h3>
                <p className="text-xs text-hive-muted">
                  {p.canonical_domain || p.domain} · {p.source_count} sources
                </p>
                <p className="text-sm mt-1">
                  Session: {p.session_status} · Opportunities: {p.opportunities_discovered} · Checkpoints:{" "}
                  {p.checkpoints_pending}
                </p>
              </button>
            ))
          )}
        </div>

        {selected && (
          <div className="card space-y-3">
            <h3 className="font-semibold text-hive-gold">{selected.portal_name || selected.domain}</h3>
            <div className="flex flex-wrap gap-2">
              <button
                className="btn-primary text-sm"
                disabled={!chromiumOk}
                onClick={() =>
                  runAction("Start browser", () => api.portals.startBrowser(selected.id))
                }
              >
                Start browser session
              </button>
              <button
                className="btn-secondary text-sm"
                disabled={!chromiumOk}
                onClick={() => runAction("Scan public", () => api.portals.scanPublic(selected.id))}
              >
                Scan public page
              </button>
              <button
                className="btn-secondary text-sm"
                disabled={!chromiumOk}
                onClick={() => runAction("Scan with session", () => api.portals.scanWithSession(selected.id))}
              >
                Scan with saved session
              </button>
              {activeRun && (
                <>
                  <button
                    className="btn-secondary text-sm"
                    onClick={() =>
                      runAction("Continue", () => api.portals.continueCheckpoint(activeRun.id))
                    }
                  >
                    Continue after checkpoint
                  </button>
                  <button
                    className="btn-secondary text-sm"
                    onClick={() =>
                      runAction("Save session", () => api.portals.saveRunSession(activeRun.id))
                    }
                  >
                    Save session
                  </button>
                </>
              )}
              <button
                className="btn-secondary text-sm text-red-300"
                onClick={() => runAction("Delete session", () => api.portals.cleanupSession(selected.id))}
              >
                Delete session
              </button>
              {selected.portal_url && (
                <a href={selected.portal_url} target="_blank" rel="noreferrer" className="btn-secondary text-sm">
                  Open portal (your browser)
                </a>
              )}
            </div>

            {activeRun && (
              <div className="border border-hive-border rounded p-3 text-sm space-y-2">
                <p>
                  Run #{activeRun.id} · <span className="text-hive-gold">{activeRun.status}</span>
                </p>
                {activeRun.current_url && (
                  <p className="text-xs break-all text-hive-muted">{activeRun.current_url}</p>
                )}
                {activeRun.checkpoint && (
                  <div className="bg-amber-900/20 p-2 rounded text-amber-200 text-xs">
                    <p className="font-medium">Checkpoint: {activeRun.checkpoint.type}</p>
                    <p>{activeRun.checkpoint.instruction}</p>
                  </div>
                )}
                {activeRun.errors && <p className="text-red-300">{activeRun.errors}</p>}
                {screenshotUrl && (
                  <img src={screenshotUrl} alt="Portal screenshot" className="rounded border border-hive-border max-h-64" />
                )}
              </div>
            )}

            <div>
              <h4 className="font-medium text-sm mb-2">Discovered opportunities ({opportunities.length})</h4>
              <ul className="max-h-48 overflow-auto space-y-2 text-sm">
                {opportunities.map((o) => (
                  <li key={o.id} className="border-t border-hive-border pt-2">
                    <p className="font-medium">{o.title}</p>
                    {o.application_url && (
                      <a href={o.application_url} className="text-xs text-hive-gold" target="_blank" rel="noreferrer">
                        Application link
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
