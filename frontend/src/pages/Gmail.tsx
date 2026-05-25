import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ConfigBanner } from "../components/ConfigBanner";
import { Loading } from "../components/Loading";

export default function GmailPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [scanResult, setScanResult] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.gmail.status().then((s) => setStatus(s)).finally(() => setLoading(false));
  }, []);

  const connect = async () => {
    const r = await api.gmail.authUrl();
    if (r.auth_url) window.open(r.auth_url, "_blank");
    else alert(r.message || "Gmail not configured");
  };

  const scan = async () => {
    const r = await api.gmail.scan();
    setScanResult(String(r.message));
  };

  if (loading) return <Loading />;

  const configured = !!status?.configured;
  const connected = !!status?.connected;

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-6">Gmail Scanner</h2>
      {!configured && (
        <ConfigBanner message="Gmail not configured — set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI" />
      )}
      <div className="card max-w-xl">
        <p className="text-sm">
          Status: <strong>{String(status?.status)}</strong>
        </p>
        <p className="text-sm text-hive-muted mt-2">{String(status?.message)}</p>
        <p className="text-xs text-hive-muted mt-4">
          Read-only scope · Scholarship-related search terms only · No outbound email in MVP
        </p>
        <div className="flex gap-3 mt-6">
          <button className="btn-primary" onClick={connect} disabled={!configured}>
            Connect Gmail
          </button>
          <button className="btn-secondary" onClick={scan} disabled={!connected}>
            Scan Gmail Now
          </button>
        </div>
        {scanResult && <p className="text-sm text-emerald-300 mt-4">{scanResult}</p>}
      </div>
    </div>
  );
}
