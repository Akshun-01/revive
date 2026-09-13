// HTTP client for the Revive backend (API contract v0.3). Base URL from NEXT_PUBLIC_API_BASE.

import type {
  Approval, Connection, CustomerSummary, Investigation, InvestigationSummary, Provider, ReviveClient,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const API = `${API_BASE}/api/v1`;

// Stub auth until real per-user auth lands: a fixed user id on every request.
export const USER_ID = process.env.NEXT_PUBLIC_USER_ID ?? "demo-user";
const HEADERS = { "X-User-Id": USER_ID };

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let detail = text;
    try { const parsed = JSON.parse(text); if (parsed && typeof parsed.detail === "string") detail = parsed.detail; } catch { /* not JSON */ }
    throw new Error(detail ? detail.slice(0, 300) : `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

const get = (path: string) => fetch(`${API}${path}`, { headers: HEADERS, cache: "no-store" });
const post = (path: string, body: unknown) =>
  fetch(`${API}${path}`, { method: "POST", headers: { ...HEADERS, "Content-Type": "application/json" }, body: JSON.stringify(body) });
const del = (path: string) => fetch(`${API}${path}`, { method: "DELETE", headers: HEADERS });

// SSE stream of a live run. Returns an unsubscribe function. EventSource cannot set headers,
// so the stub user id is passed as a query param (matches the backend's stream endpoints).
export function streamInvestigation(
  customer: string,
  onEvent: (name: string, data: Record<string, unknown>) => void,
  onError?: (err: unknown) => void,
): () => void {
  const url = `${API}/investigations/stream?customer=${encodeURIComponent(customer)}&user_id=${encodeURIComponent(USER_ID)}`;
  return openStream(url, onEvent, onError);
}

export function streamResume(
  investigationId: string,
  approved: boolean,
  onEvent: (name: string, data: Record<string, unknown>) => void,
  onError?: (err: unknown) => void,
): () => void {
  const url = `${API}/investigations/${investigationId}/resume-stream?approved=${approved}&user_id=${encodeURIComponent(USER_ID)}`;
  return openStream(url, onEvent, onError);
}

const STREAM_EVENTS = [
  "investigation_started", "customer_resolved", "evidence_collected", "diagnosis_completed",
  "recoverability_decided", "intervention_selected", "actions_planned", "approval_required",
  "action_executed", "action_verified", "investigation_completed",
];

function openStream(url: string, onEvent: (name: string, data: Record<string, unknown>) => void, onError?: (err: unknown) => void): () => void {
  const es = new EventSource(url);
  for (const name of STREAM_EVENTS) {
    es.addEventListener(name, (ev) => {
      let data: Record<string, unknown> = {};
      try { data = (ev as MessageEvent).data ? JSON.parse((ev as MessageEvent).data) : {}; } catch { /* keep empty */ }
      onEvent(name, data);
      if (name === "investigation_completed" || name === "approval_required") es.close();
    });
  }
  es.onerror = (e) => onError?.(e);
  return () => es.close();
}

export const client: ReviveClient = {
  health: () => get("/health").then((r) => json(r)),

  startInvestigation: (customer): Promise<Investigation> =>
    post("/investigations", { customer }).then((r) => json(r)),

  getInvestigation: (id): Promise<Investigation> => get(`/investigations/${id}`).then((r) => json(r)),

  listCustomers: (): Promise<CustomerSummary[]> => get("/customers").then((r) => json(r)),

  listInvestigations: (): Promise<InvestigationSummary[]> => get("/investigations").then((r) => json(r)),

  listApprovals: (): Promise<Approval[]> => get("/approvals").then((r) => json(r)),

  approve: (investigationId, edits): Promise<Investigation> =>
    post(`/approvals/${investigationId}/approve`, edits ? { edits } : {}).then((r) => json(r)),

  reject: (investigationId, reason): Promise<Investigation> =>
    post(`/approvals/${investigationId}/reject`, { reason }).then((r) => json(r)),

  listConnections: (): Promise<Connection[]> => get("/connections").then((r) => json(r)),

  connect: (provider: Provider, credentials, scopes = []): Promise<Connection> =>
    post("/connections", { provider, credentials, scopes }).then((r) => json(r)),

  async disconnect(provider: Provider) {
    const r = await del(`/connections/${provider}`);
    if (!r.ok && r.status !== 404) await json(r); // 404 = already gone, treat as success
  },
};
