const API_BASE = import.meta.env.VITE_API_URL || "";

export async function request<T = unknown>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.message || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request<Record<string, unknown>>("/health"),
  profile: {
    get: () => request<Record<string, unknown>>("/api/profile"),
    update: (data: object) => request<Record<string, unknown>>("/api/profile", { method: "PUT", body: JSON.stringify(data) }),
  },
  stories: {
    list: () => request<unknown[]>("/api/stories"),
    create: (data: object) => request("/api/stories", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: object) =>
      request(`/api/stories/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request(`/api/stories/${id}`, { method: "DELETE" }),
  },
  scholarships: {
    list: (filter?: string) =>
      request<unknown[]>(`/api/scholarships${filter ? `?filter=${filter}` : ""}`),
    get: (id: number) => request<unknown>(`/api/scholarships/${id}`),
    create: (data: object) =>
      request("/api/scholarships", { method: "POST", body: JSON.stringify(data) }),
    evaluate: (id: number) => request(`/api/scholarships/${id}/evaluate`, { method: "POST" }),
    moveStatus: (id: number, status: string, next_action?: string) =>
      request(`/api/scholarships/${id}/move-status`, {
        method: "POST",
        body: JSON.stringify({ status, next_action }),
      }),
    applyPrep: (id: number) => request(`/api/scholarships/${id}/apply-prep`),
    markSuspects: () =>
      request<{ marked: number; message: string }>("/api/scholarships/mark-suspects-review", { method: "POST" }),
    reject: (id: number, reason: string) =>
      request(`/api/scholarships/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  },
  essays: {
    list: () => request<unknown[]>("/api/essays"),
    generate: (scholarship_id: number) =>
      request("/api/essays/generate", { method: "POST", body: JSON.stringify({ scholarship_id }) }),
    review: (id: number) => request<{ message: string; authenticity_score: number }>(`/api/essays/${id}/review`, { method: "POST" }),
    update: (id: number, data: object) =>
      request(`/api/essays/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    approve: (id: number) => request(`/api/essays/${id}/approve`, { method: "POST" }),
    rewrite: (id: number, mode: string) =>
      request<Record<string, unknown>>(`/api/essays/${id}/rewrite`, {
        method: "POST",
        body: JSON.stringify({ mode }),
      }),
  },
  webSearch: {
    status: () => request<Record<string, unknown>>("/api/web-search/status"),
    run: (query?: string) =>
      request<Record<string, unknown>>("/api/web-search/run", {
        method: "POST",
        body: JSON.stringify(query ? { query } : {}),
      }),
  },
  gmail: {
    status: () => request<Record<string, unknown>>("/api/gmail/status"),
    authUrl: () => request<{ auth_url?: string; message?: string }>("/api/gmail/auth-url"),
    scan: (days = 30) => request<Record<string, unknown>>(`/api/gmail/scan?days=${days}`, { method: "POST" }),
    listMessages: () => request<unknown[]>("/api/gmail/messages"),
    getMessage: (id: number) => request<Record<string, unknown>>(`/api/gmail/messages/${id}`),
    rejectMessage: (id: number) => request(`/api/gmail/messages/${id}/reject`, { method: "POST" }),
  },
  memoryVault: {
    overview: () => request<Record<string, unknown>>("/api/memory-vault/overview"),
    paste: (text: string, title: string, source_type: string) =>
      request("/api/memory-vault/paste", {
        method: "POST",
        body: JSON.stringify({ text, title, source_type }),
      }),
    upload: async (file: File, source_type: string) => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("source_type", source_type);
      const res = await fetch(`${API_BASE}/api/memory-vault/upload`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || err.message || `HTTP ${res.status}`);
      }
      return res.json();
    },
    conflicts: () => request<unknown[]>("/api/memory-vault/conflicts"),
    confirm: (id: number) => request(`/api/memory-vault/nodes/${id}/confirm`, { method: "POST" }),
    reject: (id: number) => request(`/api/memory-vault/nodes/${id}/reject`, { method: "POST" }),
    bulkApprove: () => request("/api/memory-vault/bulk-approve-high-confidence", { method: "POST" }),
    syncLegacy: () => request("/api/memory-vault/sync-legacy", { method: "POST" }),
  },
  telegram: {
    status: () => request<Record<string, unknown>>("/api/telegram/status"),
    getConfig: () => request<Record<string, unknown>>("/api/telegram/config"),
    diagnostics: () => request<Record<string, unknown>>("/api/telegram/diagnostics"),
    saveConfig: (chat_id: string) =>
      request("/api/telegram/config", { method: "PUT", body: JSON.stringify({ chat_id }) }),
    sendTest: (chat_id?: string) =>
      request<Record<string, unknown>>("/api/telegram/send-test", {
        method: "POST",
        body: JSON.stringify(chat_id ? { chat_id } : {}),
      }),
    sendQuestion: (request_id: number, chat_id?: string) =>
      request("/api/telegram/send-question", {
        method: "POST",
        body: JSON.stringify({ request_id, chat_id }),
      }),
  },
  portals: {
    list: (showTracking = false) =>
      request<unknown[]>(`/api/portals${showTracking ? "?show_tracking=true" : ""}`),
    agentStatus: () => request<Record<string, unknown>>("/api/portals/agent-status"),
    startBrowser: (id: number) =>
      request<Record<string, unknown>>(`/api/portals/${id}/start-browser-session`, { method: "POST" }),
    openSession: (id: number) => request<Record<string, unknown>>(`/api/portals/${id}/open-session`, { method: "POST" }),
    scanPublic: (id: number) =>
      request<Record<string, unknown>>(`/api/portals/${id}/scan-public`, { method: "POST" }),
    scanWithSession: (id: number) =>
      request<Record<string, unknown>>(`/api/portals/${id}/scan-with-session`, { method: "POST" }),
    continueCheckpoint: (runId: number) =>
      request<Record<string, unknown>>(`/api/portals/runs/${runId}/continue-after-checkpoint`, { method: "POST" }),
    saveRunSession: (runId: number) =>
      request<Record<string, unknown>>(`/api/portals/runs/${runId}/save-session`, { method: "POST" }),
    getRun: (runId: number) => request<Record<string, unknown>>(`/api/portals/runs/${runId}`),
    screenshotUrl: (runId: number) => `${import.meta.env.VITE_API_URL || ""}/api/portals/runs/${runId}/screenshot`,
    opportunities: (portalId: number) => request<unknown[]>(`/api/portals/${portalId}/opportunities`),
    cleanupSession: (portalId: number) =>
      request<Record<string, unknown>>(`/api/portals/${portalId}/cleanup-session`, { method: "POST" }),
  },
  profileGraph: {
    list: () => request<Record<string, unknown>>("/api/profile-graph"),
    extractText: (text: string) =>
      request("/api/profile-graph/extract-from-text", {
        method: "POST",
        body: JSON.stringify({ text, node_type: "essay themes" }),
      }),
    approve: (id: number) => request(`/api/profile-graph/nodes/${id}/approve`, { method: "POST" }),
  },
  missingInfo: {
    list: () => request<unknown[]>("/api/missing-info"),
    answer: (id: number, user_reply: string) =>
      request(`/api/missing-info/${id}/answer`, {
        method: "POST",
        body: JSON.stringify({ user_reply }),
      }),
    save: (id: number) => request(`/api/missing-info/${id}/save`, { method: "POST" }),
    dismiss: (id: number) => request(`/api/missing-info/${id}/dismiss`, { method: "POST" }),
  },
  documents: {
    list: () => request<unknown[]>("/api/documents"),
    create: (data: object) =>
      request("/api/documents", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: object) =>
      request(`/api/documents/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request(`/api/documents/${id}`, { method: "DELETE" }),
  },
  dashboard: () => request<Record<string, unknown>>("/api/dashboard/summary"),
  settings: () => request<Record<string, Record<string, unknown>>>("/api/settings/status"),
  jobs: {
    recalculate: () => request("/api/jobs/recalculate-eligibility", { method: "POST" }),
    scanGmail: () => request("/api/jobs/scan-gmail", { method: "POST" }),
  },
};
