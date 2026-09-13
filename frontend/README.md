# Revive Frontend

The investigation workspace for [Revive](../README.md), the AI revenue-recovery agent. A Next.js app where a Customer Success / RevOps user starts an investigation into a lost renewal, watches the
agent work in real time, reviews the evidence-backed diagnosis, and approves recovery actions.

**Live:** https://revive-ai-revops.vercel.app

## Features

- **Book of business.** A prioritized list of lost / at-risk renewals worth investigating (seed fixtures, or live from Stripe subscriptions in live mode).
- **Live investigation.** Starting an investigation streams the agent's trace over SSE: resolving the customer, querying each system, diagnosing, deciding recoverability, then handing off to the full workspace.
- **Evidence chain.** Evidence grouped by source (Stripe, HubSpot, Slack, Userlens) with support/contradiction tags; hovering an evidence chip on a conclusion highlights the exact items that back it.
- **Verdict + reasoning.** Revenue impact, primary cause with confidence, recoverability decision, recommended intervention, and the alternatives considered.
- **Human-in-the-loop approvals.** External / financial actions surface an approval panel (and a dedicated `/approvals` inbox). The draft is editable; nothing reaches a customer without sign-off. Actions then show as executed and verified.
- **Integrations.** Connect Stripe / HubSpot / Slack by pasting a token. Tokens are sent once to the backend, encrypted there, and never shown again.
- **Theme-aware, responsive** UI with a considered type and color system.

## Tech stack

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4 · lucide-react. No data-fetching library: a small typed client in `src/lib/api.ts` wraps the backend REST + SSE endpoints.

## Project structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx                       # home: start + book of business + recent
│   │   ├── investigations/live/page.tsx   # live SSE run, then hands off to the workspace
│   │   ├── investigations/[id]/page.tsx   # full investigation workspace
│   │   ├── approvals/page.tsx             # pending-approvals inbox
│   │   ├── settings/integrations/page.tsx # connect Stripe / HubSpot / Slack
│   │   └── layout.tsx                     # shell, nav, backend status badge
│   ├── components/                        # Workspace, LiveRun, Timeline, sections,
│   │   │                                  # ApprovalPanel, ApprovalsInbox, LostRenewals,
│   │   │                                  # ConnectionCard, IntegrationsSettings, ui, ...
│   └── lib/
│       ├── api.ts                         # typed backend client (REST + SSE)
│       ├── types.ts                       # types mirroring the backend API contract
│       ├── labels.ts                      # enum -> human labels, formatters
│       └── providers.ts                   # per-provider connect config
├── .env.example
└── package.json
```

## Getting started

### Prerequisites

- Node.js 20+
- A running Revive backend (see [`../backend/README.md`](../backend/README.md)), local or the deployed URL

### Install and run

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev            # http://localhost:3000
```

### Environment

| Variable                 | Default                   | Purpose                                                                                                                              |
| ------------------------ | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `NEXT_PUBLIC_API_BASE` | `http://127.0.0.1:8000` | Backend base URL; the client appends`/api/v1`. Use the deployed backend URL for a hosted frontend.                                 |
| `NEXT_PUBLIC_USER_ID`  | `demo-user`             | Stub auth: sent as`X-User-Id` (and as a query param on SSE streams). Keep in sync with the backend user whose connections you use. |

`NEXT_PUBLIC_*` values are inlined at build time, so changing them requires a rebuild / redeploy.

## Scripts

```bash
npm run dev      # dev server
npm run build    # production build (type-checks the whole app)
npm run start    # serve the production build
npm run lint     # eslint
```

## Backend contract

The client in `src/lib/api.ts` and the types in `src/lib/types.ts` mirror the backend API
(`../backend/docs/API.md`). Key endpoints used:

- `GET /health`, `GET /customers`, `GET/POST /investigations`, `GET /investigations/{id}`
- `GET /investigations/stream`, `GET /investigations/{id}/resume-stream` (SSE)
- `GET /approvals`, `POST /approvals/{id}/approve|reject`, `POST /investigations/{id}/resume`
- `GET/POST/DELETE /connections`

The backend enables permissive CORS, so the deployed frontend can call the deployed backend directly.

## Deployment (Vercel)

1. Import the repo into Vercel with the `frontend/` directory as the project root.
2. Set `NEXT_PUBLIC_API_BASE` to your backend URL (for example `https://revive-api.log0.in`) and `NEXT_PUBLIC_USER_ID`.
3. Deploy. Because these are build-time values, redeploy after changing them.
