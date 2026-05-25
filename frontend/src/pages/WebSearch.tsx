import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ConfigBanner } from "../components/ConfigBanner";
import { Loading } from "../components/Loading";

export default function WebSearch() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [query, setQuery] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.webSearch.status().then(setStatus).finally(() => setLoading(false));
  }, []);

  const run = async () => {
    setRunning(true);
    setResult(null);
    try {
      const r = await api.webSearch.run(query.trim() || undefined);
      setResult(r);
      api.webSearch.status().then(setStatus);
    } catch (e: unknown) {
      setResult({ message: e instanceof Error ? e.message : "Search failed" });
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <Loading />;

  const configured = !!status?.configured;
  const last = status?.last_run as Record<string, unknown> | null;

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-2">Web Scholarship Search</h2>
      <p className="text-sm text-hive-muted mb-6">
        Powered by Tavily — manual run only. Results are structured with Gemini when configured.
      </p>

      {!configured && (
        <ConfigBanner message="Web Search not configured — add TAVILY_API_KEY in Railway." />
      )}

      <div className="card max-w-2xl space-y-4">
        <p className="text-sm">
          Status: <strong>{configured ? "Configured" : "Not configured"}</strong>
        </p>
        <input
          className="input-field"
          placeholder="Custom search query (optional)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button className="btn-primary" onClick={run} disabled={!configured || running}>
          {running ? "Searching…" : "Run Web Scholarship Search"}
        </button>
        {last && (
          <div className="text-xs text-hive-muted border-t border-hive-border pt-3 space-y-1">
            <p>Last run: {String(last.started_at)}</p>
            <p>Query: {String(last.search_query)}</p>
            <p>Saved: {String(last.saved_count)} · Duplicates skipped: {String(last.duplicates_skipped)}</p>
            <p>Low-trust skipped: {String(last.low_trust_skipped)}</p>
            {last.errors ? <p className="text-amber-300">Errors: {String(last.errors)}</p> : null}
          </div>
        )}
      </div>

      {result && (
        <div className="card mt-6 max-w-2xl text-sm space-y-2">
          <p className="text-hive-gold font-semibold">Last search result</p>
          <p>{String(result.message)}</p>
          {"saved" in result && <p>New saved: {String(result.saved)}</p>}
          {"duplicates_skipped" in result && <p>Duplicates skipped: {String(result.duplicates_skipped)}</p>}
          {"low_trust_skipped" in result && <p>Low-trust skipped: {String(result.low_trust_skipped)}</p>}
          {Array.isArray(result.errors) && (result.errors as string[]).length > 0 && (
            <ul className="text-amber-300 list-disc pl-5">
              {(result.errors as string[]).map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
