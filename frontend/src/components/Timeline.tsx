"use client";

import clsx from "clsx";
import type { InvestigationEvent, InvestigationStatus } from "@/lib/types";
import { SOURCE_LABEL, clock } from "@/lib/labels";
import { Micro } from "./ui";

function describe(e: InvestigationEvent): { who: string; what: string } {
  const d = e.data as Record<string, string | number | boolean | undefined>;
  switch (e.name) {
    case "customer_resolved": return { who: "Agent", what: `Resolved ${d.name ?? "customer"} across systems` };
    case "evidence_source_started": return { who: SOURCE_LABEL[d.source as keyof typeof SOURCE_LABEL] ?? String(d.source), what: "Querying…" };
    case "evidence_source_completed": return { who: SOURCE_LABEL[d.source as keyof typeof SOURCE_LABEL] ?? String(d.source), what: `${d.evidence_count ?? 0} evidence item${d.evidence_count === 1 ? "" : "s"}` };
    case "diagnosis_started": return { who: "Agent", what: "Correlating evidence" };
    case "diagnosis_completed": return { who: "Agent", what: `Cause: ${String(d.primary_cause ?? "").replace(/_/g, " ")} (${Math.round(Number(d.confidence ?? 0) * 100)}%)` };
    case "approval_required": return { who: "Policy", what: "Approval required for external action" };
    case "action_executed": return { who: "Agent", what: String(d.message ?? `Executed ${d.action_id}`) };
    case "action_verified": return { who: "Agent", what: d.verified ? "Verified against source system" : "Verification failed" };
    case "investigation_completed": return { who: "Agent", what: `Investigation ${String(d.status ?? "complete")}` };
  }
}

export function Timeline({ events, status }: { events: InvestigationEvent[]; status: InvestigationStatus | null }) {
  // Collapse "started" rows once the matching "completed" row arrives.
  const rows = events.filter((e, i) => !(e.name === "evidence_source_started" && events.slice(i + 1).some((x) => x.name === "evidence_source_completed" && x.data.source === e.data.source)));
  const live = status === "running" || status === "created";
  return (
    <div className="border border-line bg-surface">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <Micro className="!text-ink">Investigation trace</Micro>
        <Micro>{rows.length} steps</Micro>
      </div>
      <ol className="divide-y divide-line">
        {rows.map((e, i) => {
          const { who, what } = describe(e);
          const isLast = i === rows.length - 1;
          const pending = e.name === "evidence_source_started" || (isLast && live && e.name !== "investigation_completed");
          return (
            <li key={`${e.name}-${i}`} className="rise grid grid-cols-[52px_72px_1fr] items-start gap-2 px-4 py-2 text-[12.5px]">
              <span className="num text-ink-3">{clock(e.at)}</span>
              <span className={clsx("truncate font-medium", who === "Policy" && "text-amber")}>{who}</span>
              <span className={clsx("text-ink-2", pending && "pulse")}>{what}</span>
            </li>
          );
        })}
        {rows.length === 0 && <li className="pulse px-4 py-3 text-[12.5px] text-ink-3">Connecting to agent…</li>}
        {live && rows.length > 0 && rows[rows.length - 1].name !== "investigation_completed" && (
          <li className="grid grid-cols-[52px_72px_1fr] gap-2 px-4 py-2 text-[12.5px]"><span /><span /><span className="pulse text-ink-3">working…</span></li>
        )}
      </ol>
    </div>
  );
}
