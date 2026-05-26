import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading, EmptyState } from "../components/Loading";
import { ConfigBanner } from "../components/ConfigBanner";

type Portal = {
  id: number;
  domain: string;
  canonical_domain?: string;
  domain_status?: string;
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

type OppStats = { accepted: number; rejected: number; needs_review: number };

type Opportunity = {
  id: number;
  title: string;
  portal_url?: string;
  application_url?: string;
  canonical_url?: string;
  deadline?: string;
  award_amount?: string;
  quality_status?: string;
  quality_reason?: string;
  quality_score?: number;
  link_classification?: string;
};

type TrustedPlatform = {
  platform_key: string;
  name: string;
  portal_id?: number | null;
  portal_domain?: string;
  portal_url?: string;
  session_status?: string;
  opportunities_discovered?: number;
  checkpoints_pending?: number;
};

type IgnoredSource = {
  id: number;
  domain: string;
  domain_status?: string;
  reason?: string;
};

export default function Portals() {
  const [tab, setTab] = useState<"trusted" | "ignored" | "advanced">("trusted");
  const [portals, setPortals] = useState<Portal[]>([]);
  const [trustedPlatforms, setTrustedPlatforms] = useState<TrustedPlatform[]>([]);
  const [ignored, setIgnored] = useState<IgnoredSource[]>([]);
  const [agent, setAgent] = useState<AgentStatus>({});
  const [showRejected, setShowRejected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activeRun, setActiveRun] = useState<RunState | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [oppStats, setOppStats] = useState<OppStats>({ accepted: 0, rejected: 0, needs_review: 0 });
  const [message, setMessage] = useState("");
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    const portalReq =
      tab === "advanced"
        ? api.portals.list(false, true)
        : tab === "ignored"
          ? Promise.resolve([])
          : api.portals.list();
    Promise.all([
      portalReq,
      api.portals.agentStatus(),
      api.trustedPlatforms.list(),
      api.trustedPlatforms.ignoredSources(),
    ]).then(([p, a, tp, ig]) => {
      setPortals(p as Portal[]);
      setTrustedPlatforms(tp as TrustedPlatform[]);
      setIgnored(ig as IgnoredSource[]);
      setAgent(a as AgentStatus);
      setLoading(false);
    });
  };

  const loadOpportunities = async (portalId: number, rejected: boolean) => {
    const [opps, stats] = await Promise.all([
      api.portals.opportunities(portalId, rejected),
      api.portals.opportunityStats(portalId),
    ]);
    setOpportunities(opps as Opportunity[]);
    setOppStats(stats as OppStats);
  };

  useEffect(() => {
    load();
  }, [tab]);

  useEffect(() => {
    if (selectedId) {
      loadOpportunities(selectedId, showRejected);
    }
  }, [selectedId, showRejected]);

  const selectPortal = async (id: number) => {
    setSelectedId(id);
    setActiveRun(null);
    setScreenshotUrl(null);
    setShowRejected(false);
    await loadOpportunities(id, false);
  };

  const runAction = async (label: string, fn: () => Promise<Record<string, unknown>>) => {
    setMessage(`${label}…`);
    setScreenshotUrl(null);
    try {
      const r = await fn();
      const err = r.error ? String(r.error) : "";
      if (r.success === false) {
        setMessage(err || String(r.message || "Run failed"));
      } else {
        setMessage(String(r.message || JSON.stringify(r)));
      }
      if (r.run_id || r.portal_run_id) {
        const runId = Number(r.run_id || r.portal_run_id);
        const run = (await api.portals.getRun(runId)) as RunState & { screenshot_url?: string };
        setActiveRun(run);
        const shot =
          typeof r.screenshot_url === "string"
            ? r.screenshot_url
            : run.screenshot_url || null;
        setScreenshotUrl(
          shot && run.status !== "failed" ? api.portals.screenshotUrl(runId) : null
        );
      }
      if (selectedId) {
        await loadOpportunities(selectedId, showRejected);
      }
      load();
    } catch (e: unknown) {
      setMessage(e instanceof Error ? e.message : "Action failed");
    }
  };

  const setQuality = async (oppId: number, status: string) => {
    await api.portals.setOpportunityQuality(oppId, status);
    if (selectedId) {
      await loadOpportunities(selectedId, showRejected);
      load();
    }
  };

  if (loading) return <Loading />;

  const chromiumOk = !!agent.chromium_available;
  const selected = portals.find((p) => p.id === selectedId);

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-2">Trusted Platforms</h2>
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

      <div className="flex flex-wrap gap-2 mb-4">
        {(["trusted", "ignored", "advanced"] as const).map((t) => (
          <button
            key={t}
            type="button"
            className={`text-sm px-3 py-1 rounded-full border ${
              tab === t ? "border-hive-gold text-hive-gold" : "border-hive-border text-hive-muted"
            }`}
            onClick={() => setTab(t)}
          >
            {t === "trusted" ? "Trusted Platforms" : t === "ignored" ? "Ignored Sources" : "Advanced / All"}
          </button>
        ))}
        <button
          type="button"
          className="btn-secondary text-sm"
          onClick={() =>
            runAction("Apply cleanup", () => api.trustedPlatforms.applyCleanup())
          }
        >
          Apply Trusted Platform Cleanup
        </button>
      </div>

      {tab === "advanced" && (
        <p className="text-xs text-amber-200/80 mb-4 p-2 rounded bg-amber-900/20">
          Broad discovery is disabled. Only manually trust a source if you are sure.
        </p>
      )}

      {message && <p className="text-sm mb-4 p-2 rounded bg-hive-panel">{message}</p>}

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="space-y-3">
          {tab === "ignored" ? (
            ignored.length === 0 ? (
              <EmptyState title="No ignored sources" hint="Cleanup will mark non-trusted domains here." />
            ) : (
              ignored.map((s) => (
                <div key={s.id} className="card text-sm">
                  <p className="font-medium">{s.domain}</p>
                  <p className="text-xs text-hive-muted">{s.domain_status} · {s.reason}</p>
                </div>
              ))
            )
          ) : tab === "trusted" ? (
            trustedPlatforms.length === 0 ? (
              <EmptyState title="No trusted platforms" hint="Seed or cleanup to register platforms." />
            ) : (
              trustedPlatforms.map((tp) => (
                <button
                  key={tp.platform_key}
                  onClick={() => tp.portal_id && selectPortal(tp.portal_id)}
                  className={`card w-full text-left ${selectedId === tp.portal_id ? "border-hive-gold/50" : ""}`}
                >
                  <h3 className="font-semibold">{tp.name}</h3>
                  <p className="text-xs text-hive-muted">{tp.portal_domain}</p>
                  <p className="text-sm mt-1">
                    Session: {tp.session_status} · Opportunities: {tp.opportunities_discovered} ·
                    Checkpoints: {tp.checkpoints_pending}
                  </p>
                </button>
              ))
            )
          ) : portals.length === 0 ? (
            <EmptyState title="No portals" hint="Advanced view — all portal records." />
          ) : (
            portals.map((p) => (
              <button
                key={p.id}
                onClick={() => selectPortal(p.id)}
                className={`card w-full text-left ${selectedId === p.id ? "border-hive-gold/50" : ""}`}
              >
                <h3 className="font-semibold">{p.portal_name || p.domain}</h3>
                <p className="text-xs text-hive-muted">
                  {p.canonical_domain || p.domain}
                  {p.domain_status && p.domain_status !== "active" ? ` · ${p.domain_status}` : ""} ·{" "}
                  {p.source_count} sources
                </p>
                <p className="text-sm mt-1">
                  Session: {p.session_status} · Accepted opportunities: {p.opportunities_discovered} ·
                  Checkpoints: {p.checkpoints_pending}
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
                {screenshotUrl ? (
                  <img
                    src={screenshotUrl}
                    alt="Portal screenshot"
                    className="rounded border border-hive-border max-h-64"
                    onError={() => setScreenshotUrl(null)}
                  />
                ) : activeRun.status === "failed" ? (
                  <p className="text-xs text-hive-muted">No screenshot available for this failed run.</p>
                ) : null}
              </div>
            )}

            <div>
              <p className="text-xs text-hive-muted mb-2">
                Accepted: {oppStats.accepted} · Needs review: {oppStats.needs_review} · Ignored/rejected:{" "}
                {oppStats.rejected}
              </p>
              <label className="flex items-center gap-2 text-sm text-hive-muted mb-2">
                <input
                  type="checkbox"
                  checked={showRejected}
                  onChange={(e) => setShowRejected(e.target.checked)}
                />
                Show ignored / rejected links
              </label>
              <h4 className="font-medium text-sm mb-2">
                {showRejected ? "Ignored links" : "Accepted opportunities"} ({opportunities.length})
              </h4>
              <ul className="max-h-64 overflow-auto space-y-2 text-sm">
                {opportunities.map((o) => (
                  <li key={o.id} className="border-t border-hive-border pt-2">
                    <p className="font-medium">{o.title}</p>
                    <p className="text-xs text-hive-muted">
                      {o.link_classification} · score {o.quality_score} · {o.quality_status}
                    </p>
                    {o.quality_reason && (
                      <p className="text-xs text-hive-muted italic">{o.quality_reason}</p>
                    )}
                    {(o.canonical_url || o.application_url) && (
                      <a
                        href={o.canonical_url || o.application_url}
                        className="text-xs text-hive-gold break-all"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open source
                      </a>
                    )}
                    <div className="flex gap-2 mt-1">
                      {o.quality_status !== "accepted" && (
                        <button
                          type="button"
                          className="text-xs text-hive-gold"
                          onClick={() => setQuality(o.id, "accepted")}
                        >
                          Mark accepted
                        </button>
                      )}
                      {o.quality_status !== "rejected" && (
                        <button
                          type="button"
                          className="text-xs text-red-300"
                          onClick={() => setQuality(o.id, "rejected")}
                        >
                          Reject
                        </button>
                      )}
                      {o.quality_status !== "needs_review" && (
                        <button
                          type="button"
                          className="text-xs text-hive-muted"
                          onClick={() => setQuality(o.id, "needs_review")}
                        >
                          Needs review
                        </button>
                      )}
                    </div>
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
