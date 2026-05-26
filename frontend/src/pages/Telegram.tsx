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

type Diagnostics = {
  telegram_configured?: boolean;
  chat_id_saved?: boolean;
  token_format_valid?: boolean;
  get_me_ok?: boolean;
  bot_username?: string;
  webhook_url?: string | null;
  checks?: Array<{ name: string; ok: boolean; detail: string }>;
  last_test_status?: string;
  last_test_message?: string;
  last_error_code?: number;
  last_error_description?: string;
};

type TestResult = {
  success?: boolean;
  message?: string;
  next_step?: string;
  telegram_error_code?: number;
  telegram_error_description?: string;
};

export default function TelegramPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [chatId, setChatId] = useState("");
  const [requests, setRequests] = useState<Req[]>([]);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [s, c, r, d] = await Promise.all([
        api.telegram.status(),
        api.telegram.getConfig(),
        api.missingInfo.list(),
        api.telegram.diagnostics(),
      ]);
      setStatus(s);
      setConfig(c);
      setChatId(String((c as Record<string, unknown>).chat_id || ""));
      setRequests(r as Req[]);
      setDiagnostics(d as Diagnostics);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <Loading />;

  const saveAndTest = async () => {
    await api.telegram.saveConfig(chatId);
    await load();
    const res = (await api.telegram.sendTest(chatId || undefined)) as TestResult;
    setTestResult(res);
    await load();
  };

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-6">Telegram</h2>
      {!status?.configured && (
        <ConfigBanner message="Telegram not configured — set TELEGRAM_BOT_TOKEN in Railway." />
      )}

      <div className="card max-w-lg mb-6 space-y-3">
        <label className="text-sm text-hive-muted">Your Telegram chat ID (saved in database)</label>
        <input className="input-field" value={chatId} onChange={(e) => setChatId(e.target.value)} placeholder="e.g. 123456789" />
        <div className="flex flex-wrap gap-2">
          <button
            className="btn-primary"
            onClick={() => api.telegram.saveConfig(chatId).then(() => { setTestResult({ success: true, message: "Chat ID saved." }); load(); })}
          >
            Save chat ID
          </button>
          <button className="btn-secondary" onClick={() => api.telegram.diagnostics().then((d) => setDiagnostics(d as Diagnostics))}>
            Run diagnostics
          </button>
          <button className="btn-secondary" onClick={saveAndTest}>
            Send test
          </button>
        </div>

        {testResult && (
          <div className={`text-sm p-3 rounded ${testResult.success ? "bg-emerald-900/30 text-emerald-200" : "bg-red-900/30 text-red-200"}`}>
            <p className="font-medium">{testResult.success ? "Success" : "Failed"}: {testResult.message}</p>
            {testResult.telegram_error_code != null && (
              <p className="text-xs mt-1">Telegram error {testResult.telegram_error_code}: {testResult.telegram_error_description}</p>
            )}
            {testResult.next_step && <p className="text-xs mt-2 text-hive-gold">Next step: {testResult.next_step}</p>}
          </div>
        )}

        {config.last_test_status && (
          <p className="text-xs text-hive-muted">
            Last test: {String(config.last_test_status)} — {String(config.last_test_message)}
          </p>
        )}
      </div>

      {diagnostics && (
        <div className="card max-w-lg mb-6">
          <h3 className="font-semibold mb-2">Diagnostics</h3>
          <ul className="text-sm space-y-1">
            {(diagnostics.checks || []).map((c) => (
              <li key={c.name} className={c.ok ? "text-emerald-300" : "text-red-300"}>
                {c.ok ? "✓" : "✗"} {c.name}: {c.detail}
              </li>
            ))}
          </ul>
          {diagnostics.bot_username && (
            <p className="text-xs text-hive-muted mt-2">Bot: @{diagnostics.bot_username}</p>
          )}
        </div>
      )}

      <div className="space-y-4">
        {requests.map((r) => (
          <div key={r.id} className="card">
            <StatusBadge status={r.status} />
            <p className="mt-2 font-medium">{r.question}</p>
            {r.user_reply && <p className="text-sm mt-2 p-2 bg-hive-panel rounded">{r.user_reply}</p>}
            <button
              className="btn-secondary text-sm mt-3"
              onClick={() => api.telegram.sendQuestion(r.id).then((res) => setTestResult(res as TestResult))}
            >
              Send via Telegram
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
