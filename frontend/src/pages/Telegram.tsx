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
  is_demo?: boolean;
};

export default function TelegramPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [requests, setRequests] = useState<Req[]>([]);
  const [chatId, setChatId] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.telegram.status(), api.missingInfo.list()]).then(([s, r]) => {
      setStatus(s);
      setRequests(r as Req[]);
      setLoading(false);
    });
  }, []);

  if (loading) return <Loading />;

  return (
    <div>
      <h2 className="text-2xl font-display text-hive-gold mb-6">Telegram Questions</h2>
      {!status?.configured && (
        <ConfigBanner message="Telegram not configured — set TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET" />
      )}
      <div className="card mb-6 max-w-md">
        <input
          className="input-field mb-2"
          placeholder="Your Telegram chat ID"
          value={chatId}
          onChange={(e) => setChatId(e.target.value)}
        />
        <button
          className="btn-secondary text-sm"
          onClick={() => chatId && api.telegram.sendTest(chatId)}
        >
          Send test message
        </button>
      </div>
      <div className="space-y-4">
        {requests.map((r) => (
          <div key={r.id} className="card">
            <div className="flex gap-2">
              <StatusBadge status={r.status} />
              {r.is_demo && <span className="badge bg-purple-500/20 text-purple-300">demo</span>}
            </div>
            <p className="mt-2 font-medium">{r.question}</p>
            {r.reason && <p className="text-sm text-hive-muted">{r.reason}</p>}
            {r.user_reply && (
              <div className="mt-3 p-3 bg-hive-panel rounded text-sm">
                <strong>Your reply:</strong> {r.user_reply}
              </div>
            )}
            <div className="flex gap-2 mt-3 flex-wrap">
              <input
                className="input-field flex-1 min-w-[200px] text-sm"
                placeholder="Record answer manually..."
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    api.missingInfo.answer(r.id, (e.target as HTMLInputElement).value).then(() =>
                      api.missingInfo.list().then(setRequests)
                    );
                  }
                }}
              />
              <button
                className="btn-secondary text-sm"
                onClick={() => chatId && api.telegram.sendQuestion(r.id, chatId)}
              >
                Send via Telegram
              </button>
              <button
                className="btn-secondary text-sm"
                onClick={() => api.missingInfo.save(r.id).then(() => api.missingInfo.list().then(setRequests))}
              >
                Mark saved
              </button>
              <button
                className="btn-secondary text-sm"
                onClick={() => api.missingInfo.dismiss(r.id).then(() => api.missingInfo.list().then(setRequests))}
              >
                Dismiss
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
