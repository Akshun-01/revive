// HTTP client for the Revive backend (API contract v0.1). Base URL comes from NEXT_PUBLIC_API_BASE.

import type { Approval, Investigation, InvestigationEvent, ReviveClient, StartResponse } from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const API = `${API_BASE}/api/v1`;

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text.slice(0, 200)}` : ""}`);
  }
  return res.json() as Promise<T>;
}

const post = (path: string, body: unknown) =>
  fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

const EVENT_NAMES: InvestigationEvent["name"][] = [
  "customer_resolved", "evidence_source_started", "evidence_source_completed", "diagnosis_started",
  "diagnosis_completed", "approval_required", "action_executed", "action_verified", "investigation_completed",
];

export const client: ReviveClient = {
  health: () => fetch(`${API}/health`, { cache: "no-store" }).then((r) => json(r)),

  startInvestigation: (customer): Promise<StartResponse> => post("/investigations", { customer }).then((r) => json(r)),

  getInvestigation: (id): Promise<Investigation> => fetch(`${API}/investigations/${id}`, { cache: "no-store" }).then((r) => json(r)),

  subscribe(id, onEvent, onError) {
    const es = new EventSource(`${API}/investigations/${id}/events`);
    for (const name of EVENT_NAMES) {
      es.addEventListener(name, (ev) => {
        const me = ev as MessageEvent;
        let data: Record<string, unknown> = {};
        try { data = me.data ? JSON.parse(me.data) : {}; } catch { /* keep empty */ }
        onEvent({ id: me.lastEventId || undefined, name, data, at: new Date().toISOString() });
        if (name === "investigation_completed") es.close();
      });
    }
    es.onerror = (e) => onError?.(e);
    return () => es.close();
  },

  listApprovals: (): Promise<Approval[]> => fetch(`${API}/approvals`, { cache: "no-store" }).then((r) => json(r)),

  approve: (id, edited) => post(`/approvals/${id}/approve`, edited ? { edited_parameters: edited } : {}).then((r) => json(r)),

  reject: (id, reason) => post(`/approvals/${id}/reject`, { reason }).then((r) => json(r)),
};
