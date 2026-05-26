import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ConfigBanner } from "../components/ConfigBanner";
import { Loading } from "../components/Loading";

type Msg = {
  id: number;
  subject?: string;
  sender?: string;
  snippet?: string;
  body_text?: string;
  classification?: string;
  classification_reason?: string;
  status?: string;
  gmail_url?: string;
  links?: string[];
};

export default function GmailPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [selected, setSelected] = useState<Msg | null>(null);
  const [scanResult, setScanResult] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    api.gmail.status().then(setStatus);
    api.gmail.listMessages().then((m) => setMessages(m as Msg[])).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const scan = async (days: number) => {
    setScanResult("Scanning…");
    const r = await api.gmail.scan(days);
    setScanResult(String((r as Record<string, unknown>).message || "Done"));
    load();
  };

  if (loading) return <Loading />;

  const configured = !!status?.configured;
  const connected = !!status?.connected;

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-6">Gmail Scanner</h2>
      {!configured && (
        <ConfigBanner message="Gmail not configured — add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in Railway." />
      )}
      <div className="card mb-6 max-w-xl">
        <p className="text-sm">Status: {String(status?.status)} — {String(status?.message)}</p>
        <p className="text-xs text-hive-muted mt-2">
          Full message classification before saving. Irrelevant emails are rejected, not saved as scholarships.
        </p>
        <div className="flex gap-2 mt-4">
          <button className="btn-primary" disabled={!connected} onClick={() => scan(7)}>
            Scan last 7 days
          </button>
          <button className="btn-secondary" disabled={!connected} onClick={() => scan(30)}>
            Scan last 30 days
          </button>
        </div>
        {scanResult && <p className="text-sm text-emerald-300 mt-3">{scanResult}</p>}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="space-y-2 max-h-[500px] overflow-auto">
          <h3 className="font-semibold text-sm text-hive-muted">Scanned emails</h3>
          {messages.length === 0 ? (
            <p className="text-sm text-hive-muted">No scanned emails yet. Run a scan after connecting Gmail.</p>
          ) : (
            messages.map((m) => (
              <button
                key={m.id}
                onClick={() => {
                  api.gmail.getMessage(m.id).then((full) => setSelected(full as Msg)).catch(() => setSelected(m));
                }}
                className="card w-full text-left p-3 hover:border-hive-gold/50"
              >
                <p className="font-medium text-sm line-clamp-1">{m.subject}</p>
                <p className="text-xs text-hive-muted">{m.classification} · {m.status}</p>
              </button>
            ))
          )}
        </div>
        {selected && (
          <div className="card">
            <h3 className="font-semibold">{selected.subject}</h3>
            <p className="text-xs text-hive-muted mt-1">{selected.sender}</p>
            <p className="text-xs mt-2">
              <span className="text-hive-gold">{selected.classification}</span> — {selected.classification_reason}
            </p>
            <div className="mt-4 p-3 bg-hive-panel rounded text-sm max-h-48 overflow-auto whitespace-pre-wrap">
              {selected.body_text || selected.snippet}
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              <a href={selected.gmail_url} target="_blank" rel="noreferrer" className="btn-secondary text-sm">
                Open in Gmail
              </a>
              <button
                className="btn-secondary text-sm"
                onClick={() => api.gmail.rejectMessage(selected.id).then(load)}
              >
                Reject as irrelevant
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
