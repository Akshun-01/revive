"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import type { InvestigationSummary } from "@/lib/types";
import { client } from "@/lib/api";
import { CAUSE_LABEL, STATUS_LABEL, clock, money, shortDate } from "@/lib/labels";
import { Button, Empty, Micro, Skeleton, Tag, type Tone } from "./ui";

const STATUS_TONE: Record<string, Tone> = { completed: "green", waiting_for_approval: "amber", rejected: "red", failed: "red", running: "blue" };

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; rows: InvestigationSummary[]; persisted: boolean }
  | { kind: "error"; message: string };

// Investigation history as the backend records it. Nothing is cached in the browser.
export function RecentInvestigations() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let alive = true;
    Promise.all([client.listInvestigations(), client.health().catch(() => null)])
      .then(([rows, health]) => { if (alive) setState({ kind: "ready", rows, persisted: health?.persistence !== "memory" }); })
      .catch((e) => { if (alive) setState({ kind: "error", message: e instanceof Error ? e.message : String(e) }); });
    return () => { alive = false; };
  }, [reloadKey]);

  return (
    <section className="border border-line bg-surface">
      <div className="flex items-center justify-between border-b border-line px-5 py-2.5">
        <Micro className="!text-ink">Recent investigations</Micro>
        {state.kind === "ready" && <Micro>{state.rows.length} recorded</Micro>}
      </div>

      {state.kind === "loading" && <div className="p-5"><Skeleton lines={3} /></div>}

      {state.kind === "error" && (
        <div className="p-5 text-[13px] text-red">
          <div className="mb-3">Could not load history: {state.message}</div>
          <Button variant="secondary" className="h-8" onClick={() => setReloadKey((k) => k + 1)}><RefreshCw size={13} /> Retry</Button>
        </div>
      )}

      {state.kind === "ready" && !state.persisted && (
        <div className="flex items-start gap-2 border-b border-amber bg-amber-bg px-5 py-2.5 text-[12.5px] text-amber">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>The backend is running without a database, so history is not kept across restarts and this list stays empty. Set <code className="num">REVIVE_DATABASE_URL</code> on the backend to persist investigations.</span>
        </div>
      )}

      {state.kind === "ready" && state.rows.length === 0 && state.persisted && (
        <div className="p-5"><Empty>Nothing yet. Pick an account above.</Empty></div>
      )}

      {state.kind === "ready" && state.rows.length > 0 && (
        <ul className="divide-y divide-line">
          {state.rows.slice(0, 12).map((r) => (
            <li key={r.id}>
              <Link href={`/investigations/${r.id}?customer=${encodeURIComponent(r.customer_name ?? "")}`}
                className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-4 px-5 py-3 text-[13.5px] hover:bg-surface-2/60">
                <span>
                  <span className="font-medium">{r.customer_name ?? r.id}</span>
                  {r.primary_cause && <span className="ml-2 text-[12px] text-ink-2">{CAUSE_LABEL[r.primary_cause]}</span>}
                </span>
                <span className="num text-[12px] text-ink-2">{r.revenue_impact != null ? money(r.revenue_impact) : ""}</span>
                <Tag tone={STATUS_TONE[r.status] ?? "neutral"}>{STATUS_LABEL[r.status]}</Tag>
                <span className="num text-[11.5px] text-ink-3">{r.created_at ? `${shortDate(r.created_at)} ${clock(r.created_at)}` : ""}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
