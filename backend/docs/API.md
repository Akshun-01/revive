# Revive Backend - API Contract (for Frontend)

Canonical REST contract the Next.js frontend builds against. Kept in sync with the
Pydantic domain models in `backend/app/domain/models/`.

**Status legend:** 🟢 implemented · 🟡 planned (build against this shape, mock until live)

- **Base URL (dev):** `http://127.0.0.1:8000`
- **API prefix:** `/api/v1`
- **MCP endpoint (other client, not for web UI):** `/mcp`
- **Content type:** `application/json` (except SSE stream)
- **CORS:** ✅ enabled (all origins, hackathon). Browser calls work.
- **Auth:** stub - send `X-User-Id` header (defaults to `demo-user`).

---

## Endpoint summary

| Method | Path | Status | Purpose |
| ------ | ---- | ------ | ------- |
| GET  | `/api/v1/health` | 🟢 | Liveness + mode |
| GET  | `/api/v1/connections` | 🟢 | List the user's connected providers |
| POST | `/api/v1/connections` | 🟢 | Connect a provider (Stripe/HubSpot/Slack) |
| DELETE | `/api/v1/connections/{provider}` | 🟢 | Disconnect a provider |
| POST | `/api/v1/investigations` | 🟢 | Start an investigation (runs synchronously, returns full result) |
| GET  | `/api/v1/investigations` | 🟢 | List investigation summaries |
| GET  | `/api/v1/investigations/{id}` | 🟢 | Full investigation result |
| POST | `/api/v1/investigations/{id}/resume` | 🟢 | Resume after approval |
| GET  | `/api/v1/approvals` | 🟢 | List pending approvals |
| POST | `/api/v1/approvals/{id}/approve` | 🟢 | Approve (id = investigation_id) |
| POST | `/api/v1/approvals/{id}/reject` | 🟢 | Reject (id = investigation_id) |
| GET  | `/api/v1/investigations/stream?customer=` | 🟢 | Start + stream progress (SSE) |
| GET  | `/api/v1/investigations/{id}/resume-stream?approved=` | 🟢 | Resume + stream after approval (SSE) |
| POST/GET | `/mcp` | 🟢 | Revive MCP server for AI clients |

Money values are numbers in USD. Timestamps are ISO-8601 strings.
User identity is sent via the `X-User-Id` header (stub auth; defaults to `demo-user`).

---

## 🟢 GET /api/v1/health

```json
{ "status": "ok", "data_source": "seed", "llm_provider": "huggingface" }
```

`data_source`: `seed` (fixtures) or `live` (real Stripe/HubSpot/Slack). Frontend does not
change behavior on this - informational.

---

## 🟢 Connections (connect your tools)

The user connects their own Stripe / HubSpot / Slack by pasting a token. Tokens are
encrypted at rest and **never returned to the browser**. Send `X-User-Id` on every call
(stub auth; defaults to `demo-user`). Build the "Integrations / Connect" screen against these.

### GET /api/v1/connections
Returns the user's connections (no secrets):
```json
[
  {
    "id": "1169c77ed5cc4558b61579294a9cd577",
    "provider": "hubspot",
    "status": "connected",
    "scopes": ["crm.read"],
    "created_at": "2026-09-13T18:15:39Z",
    "updated_at": "2026-09-13T18:15:39Z"
  }
]
```

### POST /api/v1/connections
Connect (or re-connect) a provider. `provider` is one of `stripe | hubspot | slack`.
`credentials` is a provider-specific bag (token / api_key). Idempotent per provider
(re-posting updates in place).
```json
{
  "provider": "hubspot",
  "credentials": { "token": "pat-na1-..." },
  "scopes": ["crm.read"]
}
```
Response `201` is the public Connection above - **the token is not echoed back**.

### DELETE /api/v1/connections/{provider}
Disconnect. `204` on success, `404` if not connected.

Note: `POST` requires `REVIVE_SECRET_KEY` set on the backend (Fernet key), else `400`.

---

## 🟢 POST /api/v1/investigations

Start an investigation for a customer. Runs **synchronously** (seed is instant, live is a
few seconds) and returns the full investigation object below (same shape as `GET /{id}`).
If it pauses for approval, the response has `status: "waiting_for_approval"` and a
`pending_action` - show the approval UI, then call approve/resume.

**Request**
```json
{ "customer": "Northwind Robotics" }
```

**Response** `200` - the full investigation object (see `GET /api/v1/investigations/{id}`).

`GET /api/v1/investigations` returns summaries: `{ id, customer_name, status,
revenue_impact, primary_cause, recoverability, intervention, created_at, completed_at }`.

Demo customers (seed mode): `Northwind Robotics`, `Cascade Freight`, `Meridian Analytics`, `Tidewater Systems`, `Solstice Media`.

---

## 🟢 GET /api/v1/investigations/{id}

Full investigation object. Fields fill in as the workflow progresses; nulls until a
stage completes. This is the primary object the investigation workspace renders.

```json
{
  "id": "inv_123",
  "status": "completed",
  "customer": {
    "id": "northwind",
    "name": "Northwind Robotics",
    "annual_revenue": 36000,
    "currency": "USD",
    "renewal_date": "2026-09-10T00:00:00",
    "renewal_status": "lost",
    "owner_id": "u_sarah",
    "owner_name": "Sarah Chen",
    "external_ids": { "stripe": "cus_northwind", "hubspot": "hs_northwind" }
  },
  "revenue_impact": 36000,
  "evidence": [
    {
      "id": "nw_ul1",
      "source": "userlens",
      "category": "product_behavior",
      "title": "Usage decline 67%",
      "finding": "Weekly product activity declined 67% over final 45 days. Feature X never adopted.",
      "source_reference": "userlens:nw_ul1",
      "timestamp": "2026-09-10T12:00:00",
      "confidence": 0.92,
      "supports": ["product_adoption"],
      "contradicts": []
    }
  ],
  "diagnosis": {
    "primary_cause": {
      "category": "product_adoption",
      "confidence": 0.9,
      "supporting_evidence_ids": ["nw_ul1", "nw_sl1"],
      "contradicting_evidence_ids": [],
      "reasoning": "Usage collapsed and CSM reported onboarding friction; no payment failure."
    },
    "alternatives": [
      {
        "category": "customer_support",
        "confidence": 0.3,
        "supporting_evidence_ids": ["nw_sl1"],
        "contradicting_evidence_ids": [],
        "reasoning": "Onboarding friction could read as support, but root is adoption."
      }
    ],
    "confidence": 0.9
  },
  "recoverability": {
    "decision": "recoverable",
    "confidence": 0.82,
    "factors": { "revenue_value": 0.9, "cause_confidence": 0.9, "relationship": 0.7 },
    "reasoning": "High ARR, controllable cause, engaged owner.",
    "supporting_evidence_ids": ["nw_ul1", "nw_sl1"]
  },
  "intervention": {
    "type": "targeted_onboarding",
    "priority": "high",
    "reason": "Address the adoption gap that drove non-renewal.",
    "expected_outcome": "Re-engage account, restore product value, win back renewal.",
    "risk": "Low - internal action.",
    "supporting_evidence_ids": ["nw_ul1", "nw_sl1"],
    "approval_required": false
  },
  "actions": [
    {
      "id": "action_1",
      "type": "create_crm_task",
      "description": "Create HubSpot recovery task for Sarah Chen.",
      "parameters": { "company_id": "hs_northwind", "title": "Recover Northwind", "owner_id": "u_sarah" },
      "approval_required": false,
      "status": "verified",
      "result": {
        "action_id": "action_1",
        "success": true,
        "external_reference": "task_32c27fc8",
        "message": "HubSpot task created: Recover Northwind",
        "executed_at": "2026-09-13T16:44:00Z"
      }
    }
  ],
  "verification": [
    {
      "action_id": "action_1",
      "verified": true,
      "expected_state": { "title": "Recover Northwind", "owner_id": "u_sarah" },
      "actual_state": { "title": "Recover Northwind", "owner_id": "u_sarah" },
      "discrepancies": [],
      "verified_at": "2026-09-13T16:44:01Z"
    }
  ],
  "pending_action": null,
  "audit": [
    { "seq": 0, "event_type": "customer_resolved", "payload": { "id": "northwind", "name": "Northwind Robotics" }, "at": "2026-09-13T16:42:00Z" },
    { "seq": 5, "event_type": "diagnosis_completed", "payload": { "primary_cause": "product_adoption", "confidence": 0.9 }, "at": "2026-09-13T16:43:00Z" },
    { "seq": 9, "event_type": "action_verified", "payload": { "action_id": "action_1", "verified": true }, "at": "2026-09-13T16:44:01Z" }
  ],
  "warnings": [],
  "created_at": "2026-09-13T16:42:00Z",
  "completed_at": "2026-09-13T16:44:02Z"
}
```

`audit[]` is the ordered investigation trace (persisted server-side) - render it as the
investigation timeline. Event types: `customer_resolved`, `evidence_source_completed`,
`diagnosis_completed`, `recoverability_decided`, `intervention_selected`,
`approval_required`, `action_executed`, `action_verified`.

When `status == "waiting_for_approval"`, `pending_action` holds the Action awaiting a
human decision (same shape as an `actions[]` entry, `status: "proposed"`), and there is a
matching entry in `GET /approvals`.

---

## 🟢 SSE streaming (live timeline)

`text/event-stream`. Each event is `event: <name>` + `data: <json>`. Two endpoints:

- `GET /api/v1/investigations/stream?customer=<name>&user_id=<id>` - **starts** an
  investigation and streams progress. Ends with `investigation_completed`, or
  `approval_required` if it pauses for sign-off.
- `GET /api/v1/investigations/{id}/resume-stream?approved=true&user_id=<id>` - resumes a
  paused investigation and streams the rest. Ends with `investigation_completed`.

`user_id` is a query param here (EventSource cannot set headers). Use the browser
`EventSource` API, or fetch-stream if you need the `X-User-Id` header instead.

Event names (ordered):

```
investigation_started    data: { "id": "inv_123", "customer_query": "Northwind Robotics" }
customer_resolved        data: { "id": "northwind", "name": "Northwind Robotics" }
evidence_collected       data: { "sources": { "stripe": "ok", ... }, "count": 4 }
diagnosis_completed      data: { "primary_cause": "product_adoption", "confidence": 0.9 }
recoverability_decided   data: { "decision": "recoverable", "confidence": 0.95 }
intervention_selected    data: { "type": "targeted_onboarding" }
actions_planned          data: { "count": 3 }
approval_required        data: { "investigation_id": "inv_123", "pending_action": {...} }   (pauses here)
action_executed          data: { "action_id": "act_..", "success": true, "ref": "task_.." }
action_verified          data: { "action_id": "act_..", "verified": true }
investigation_completed  data: { "status": "completed", "investigation_id": "inv_123" }
```

On `approval_required`, call `POST /approvals/{investigation_id}/approve` (or open the
resume-stream). Fallback without SSE: `POST /investigations` (sync) + poll `GET /{id}`.

---

## 🟢 Approvals (human-in-the-loop)

Financial / external actions (`send_customer_message`, `financial_mutation`) pause the
workflow. The approval is identified by its **`investigation_id`** (one pending gate per
paused investigation). You can drive this via `/approvals` or directly via
`POST /investigations/{id}/resume` with `{ "approved": true }`.

### GET /api/v1/approvals
```json
[
  {
    "investigation_id": "inv_123",
    "customer": "Northwind Robotics",
    "pending_action": {
      "id": "act_ee5476cb",
      "type": "send_customer_message",
      "description": "Send recovery outreach to Northwind Robotics.",
      "parameters": { "to": "buyer@northwind.example", "subject": "...", "body": "..." },
      "approval_required": true,
      "status": "proposed",
      "result": null
    }
  }
]
```

### POST /api/v1/approvals/{investigation_id}/approve
Optional body edits action params before executing (`{action_id: {param: value}}`):
```json
{ "edits": { "act_ee5476cb": { "body": "Revised outreach copy..." } } }
```
Returns the full completed investigation (actions executed + verified).

### POST /api/v1/approvals/{investigation_id}/reject
```json
{ "reason": "Not ready for outreach." }
```
Returns the completed investigation; the customer message is `rejected` and never sent.

Equivalent low-level call: `POST /api/v1/investigations/{id}/resume` with
`{ "approved": true|false, "edits": {...} }`.

---

## 🟢 Revive MCP server (`/mcp`)

For AI clients (Claude / ChatGPT / Cursor). Streamable-HTTP MCP at `/mcp`. Curated,
business-level tools only (no internal endpoints exposed):

```
investigate_customer(customer)                       -> full investigation
get_investigation_result(investigation_id)           -> full investigation
list_recent_investigations()                         -> summaries
resume_recovery(investigation_id, approved, edits?)  -> resumes a paused investigation
```

Same application services as REST, so behavior is identical across transports.

---

## Enums (exact string values)

Use these verbatim - backend emits lowercase snake_case.

```
InvestigationStatus : created | running | waiting_for_approval | completed | rejected | failed
EvidenceSource      : stripe | hubspot | slack | userlens
EvidenceCategory    : billing | product_behavior | crm | communication
CauseCategory       : product_adoption | pricing | payment | organizational_change |
                      customer_support | product_fit | insufficient_evidence | other
Recoverability      : recoverable | not_recoverable | insufficient_evidence
InterventionType    : billing_intervention | targeted_onboarding | commercial_review |
                      stakeholder_reengagement | support_escalation | do_not_pursue
ActionType          : create_crm_task | send_internal_notification | update_crm |
                      send_customer_message | financial_mutation
ActionStatus        : proposed | approved | rejected | executed | failed | verified
ApprovalStatus      : pending | approved | rejected
```

---

## Workspace section → data mapping (PRD §18)

| UI section | Source field |
| ---------- | ------------ |
| Header (name / ARR / status) | `customer`, `revenue_impact`, `customer.renewal_status` |
| Investigation timeline | `audit[]` (persisted trace) or SSE events |
| Financial Impact | `revenue_impact`, `evidence[source=stripe]` |
| Evidence | `evidence[]` (group by `source`; show `title`, `finding`, `confidence`) |
| Root Cause | `diagnosis.primary_cause` (+ `alternatives`) |
| Recoverability | `recoverability` |
| Recommended Action | `intervention` |
| Actions Taken | `actions[]` + `.result` |
| Verification | `verification[]` |

Evidence chain is the strongest visual element - every `diagnosis`/`recoverability`
references `*_evidence_ids` that map back to `evidence[].id`.

---

## Integration notes

- **CORS** enabled for all origins (hackathon). **Auth** is a stub: pass `X-User-Id`.
- **Interactive API docs** once endpoints land: `http://127.0.0.1:8000/docs` (Swagger),
  `/redoc`, raw schema at `/openapi.json` - generate a typed client from these.
- **Seed mode is default and deterministic** - same input → same output. Safe for building
  and demoing the UI without live credentials.
- **Amounts** are numbers (USD). **Timestamps** are ISO-8601.

## Run backend locally

```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload   # http://127.0.0.1:8000
```
