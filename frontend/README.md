# Revive frontend

Investigation workspace for the Revive revenue-recovery agent. Next.js 16, TypeScript, Tailwind v4.

```bash
npm install
cp .env.example .env.local     # set NEXT_PUBLIC_API_BASE to the backend
npm run dev                    # http://localhost:3000
```

The backend must allow CORS from `http://localhost:3000`.

## What it does

- **Home**: start an investigation by customer name, plus a list of investigations started from this browser.
- **Investigation page**: live trace from the SSE stream, evidence chain grouped by source, root cause with alternatives, recoverability with factors, recommended intervention, and actions with verification. Evidence ids referenced by the diagnosis are live links into the evidence grid.
- **Approval**: when the backend pauses with a `pending_action`, an approval panel shows the drafted message, editable before approving. Reject records a reason.
- **Settings, Integrations**: connect Stripe, HubSpot and Slack by pasting a token. Tokens go to `POST /connections` once and are never displayed or stored client-side.

## Structure

- `src/lib/types.ts`: the API contract (v0.1), enum strings verbatim.
- `src/lib/api.ts`: HTTP client. `fetch` for REST, `EventSource` for `/events`.
- `src/lib/labels.ts`: enum display labels and number/date formatting.
- `src/lib/recent.ts`: recent investigations kept in `localStorage`.
- `src/lib/providers.ts`: per-provider connect-form configuration.
- `src/components/Workspace.tsx`: the investigation page. Subscribes to `/events`, refetches the investigation on every event, polls as a fallback while running.
- `src/components/sections.tsx`: evidence, cause, recoverability, intervention and actions panels.
- `src/components/ApprovalPanel.tsx`: human approval for external actions.
- `src/components/IntegrationsSettings.tsx`, `ConnectionCard.tsx`: the integrations page.
- `src/components/ui.tsx`: primitives (panel, tag, KPI, meter, button).

## Contract notes for the backend

- Every request carries `X-User-Id` (stub auth, `NEXT_PUBLIC_USER_ID`, default `demo-user`). `EventSource` cannot set headers, so `/events` is requested without it.
- Every SSE event should carry an `id:` line; the client de-duplicates on it after reconnects.
- The approval panel resolves the approval id via `GET /approvals` filtered by `investigation_id`, then calls `approve` with `edited_parameters` only when the draft was changed.
- An action with `status: "rejected"` and a `result` on a non-approval action is rendered as "suppressed" (the already-handled case).
- `DELETE /connections/{provider}` returning `404` is treated as success (already disconnected).
