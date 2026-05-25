import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Loading } from "../components/Loading";

export default function SettingsPage() {
  const [status, setStatus] = useState<Record<string, Record<string, unknown>> | null>(null);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.settings(), api.health()]).then(([s, h]) => {
      setStatus(s);
      setHealth(h);
      setLoading(false);
    });
  }, []);

  if (loading) return <Loading />;

  const cards = status
    ? Object.entries(status).map(([key, val]) => ({
        key,
        status: String((val as Record<string, unknown>).status ?? ""),
        message: String((val as Record<string, unknown>).message ?? ""),
        configured: (val as Record<string, unknown>).configured,
      }))
    : [];

  const statusColor = (s: string) => {
    if (s.includes("configured") || s === "connected" || s === "enforced" || s === "working")
      return "text-emerald-400";
    if (s.includes("needs") || s.includes("not"))
      return "text-amber-400";
    return "text-slate-300";
  };

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-6">Settings</h2>
      <div className="grid md:grid-cols-2 gap-4">
        {cards.map((c) => (
          <div key={c.key} className="card">
            <h3 className="font-semibold capitalize">{c.key.replace(/_/g, " ")}</h3>
            <p className={`text-sm mt-2 ${statusColor(String(c.status))}`}>{String(c.status)}</p>
            <p className="text-xs text-hive-muted mt-1">{String(c.message)}</p>
          </div>
        ))}
      </div>
      {health && (
        <div className="card mt-6">
          <h3 className="font-semibold">Health endpoint snapshot</h3>
          <ul className="text-sm mt-2 space-y-1 text-hive-muted">
            <li>Database: {String(health.database)}</li>
            <li>Gemini: {health.gemini_configured ? "configured" : "not configured"}</li>
            <li>Gmail: {health.gmail_configured ? "configured" : "not configured"}</li>
            <li>Telegram: {health.telegram_configured ? "configured" : "not configured"}</li>
          </ul>
        </div>
      )}
    </div>
  );
}
