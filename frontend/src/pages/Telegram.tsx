import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ConfigBanner } from "../components/ConfigBanner";
import { Loading } from "../components/Loading";
import { StatusBadge } from "../components/StatusBadge";

type Req = {
  id: number;
  question: string;
  reason?: string;
  status: string;
  user_reply?: string;
};

export default function TelegramPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [config, setConfig] = useState<{ chat_id?: string; chat_id_saved?: boolean; last_test_status?: string; last_test_message?: string }>({});
  const [chatId, setChatId] = useState("");
  const [requests, setRequests] = useState<Req[]>([]);
  const [testResult, setTestResult] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    Promise.all([api.telegram.status(), api.telegram.getConfig(), api.missingInfo.list()]).then(
      ([s, c, r]) => {
        setStatus(s);
        const cfg = c as typeof config;
        setConfig(cfg);
        setChatId(cfg.chat_id || "");
        setRequests(r as Req[]);
      }
    );
  };

  useEffect(() => {
    load();
    setLoading(false);
  }, []);

  if (loading) return <Loading />;

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-6">Telegram Questions</h2>
      {!status?.configured && (
        <ConfigBanner message="Telegram not configured — set TELEGRAM_BOT_TOKEN in Railway." />
      )}
      <div className="card max-w-md mb-6 space-y-3">
        <label className="text-sm text-hive-muted">Your Telegram chat ID (saved in database)</label>
        <input className="input-field" value={chatId} onChange={(e) => setChatId(e.target.value)} placeholder="e.g. 123456789" />
        <button
          className="btn-primary"
          onClick={() =>
            api.telegram.saveConfig(chatId).then(() => {
              load();
              setTestResult("Chat ID saved.");
            })
          }
        >
          Save chat ID
        </button>
        <button
          className="btn-secondary"
          onClick={() =>
            api.telegram.sendTest().then((r) => {
              const res = r as Record<string, unknown>;
              setTestResult(res.success ? "Test message sent successfully." : String(res.message));
              load();
            })
          }
        >
          Send test (uses saved chat ID)
        </button>
        {testResult && <p className="text-sm text-emerald-300">{testResult}</p>}
        {config.last_test_status && (
          <p className="text-xs text-hive-muted">Last test: {config.last_test_status} — {config.last_test_message}</p>
        )}
      </div>
      <div className="space-y-4">
        {requests.map((r) => (
          <div key={r.id} className="card">
            <StatusBadge status={r.status} />
            <p className="mt-2 font-medium">{r.question}</p>
            {r.user_reply && <p className="text-sm mt-2 p-2 bg-hive-panel rounded">{r.user_reply}</p>}
            <button
              className="btn-secondary text-sm mt-3"
              onClick={() => api.telegram.sendQuestion(r.id).then((res) => setTestResult(String((res as Record<string, unknown>).message)))}
            >
              Send via Telegram
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
