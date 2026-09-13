"use client";

import clsx from "clsx";
import type { AuditEvent, InvestigationStatus } from "@/lib/types";
import { SOURCE_LABEL, clock } from "@/lib/labels";
import { Micro } from "./ui";

function describe(e: AuditEvent): { who: string; what: string } {
  const d = e.payload as Record<string, string | number | boolean | undefined>;
  switch (e.event_type) {
    case "investigation_started": return { who: "Agent", what: `Investigation started for ${d.customer_query ?? "customer"}` };
    case "customer_resolved": return { who: "Agent", what: `Resolved ${d.name ?? "customer"} across systems` };
    case "evidence_source_completed": {
      const src = SOURCE_LABEL[d.source as keyof typeof SOURCE_LABEL] ?? String(d.source);
      return { who: src, what: d.status === "ok" ? "Evidence collected" : String(d.status ?? "no data") };
    }
    case "evidence_collected": return { who: "Agent", what: `Collected evidence from ${d.count ?? 0} source${d.count === 1 ? "" : "s"}` };
    case "diagnosis_completed": return { who: "Agent", what: `Cause: ${String(d.primary_cause ?? "").replace(/_/g, " ")} (${Math.round(Number(d.confidence ?? 0) * 100)}%)` };
    case "recoverability_decided": return { who: "Agent", what: `Recoverability: ${String(d.decision ?? "").replace(/_/g, " ")} (${Math.round(Number(d.confidence ?? 0) * 100)}%)` };
    case "intervention_selected": return { who: "Agent", what: `Intervention: ${String(d.type ?? "").replace(/_/g, " ")}` };
    case "actions_planned": return { who: "Agent", what: `Planned ${d.count ?? 0} recovery action${d.count === 1 ? "" : "s"}` };
    case "approval_required": return { who: "Policy", what: "Approval required for external action" };
    case "investigation_completed": return { who: "Agent", what: `Investigation ${d.status ?? "complete"}` };
    case "action_executed": return { who: "Agent", what: d.success ? `Executed action → ${d.ref ?? ""}` : `Action failed (${d.action_id ?? ""})` };
    case "action_verified": return { who: "Agent", what: d.verified ? "Verified against source system" : "Verification failed" };
    default: return { who: "Agent", what: String(e.event_type).replace(/_/g, " ") };
  }
}

export function Timeline({ audit, status }: { audit: AuditEvent[]; status: InvestigationStatus | null }) {
  const waiting = status === "waiting_for_approval";
  return (
    <div className="border border-line bg-surface">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <Micro className="!text-ink">Investigation trace</Micro>
        <Micro>{audit.length} steps</Micro>
      </div>
      <ol className="divide-y divide-line">
        {audit.map((e, i) => {
          const { who, what } = describe(e);
          return (
            <li key={`${e.event_type}-${e.seq ?? i}`} className="rise grid grid-cols-[52px_72px_1fr] items-start gap-2 px-4 py-2 text-[12.5px]">
              <span className="num text-ink-3">{e.at ? clock(e.at) : ""}</span>
              <span className={clsx("truncate font-medium", who === "Policy" && "text-amber")}>{who}</span>
              <span className="text-ink-2">{what}</span>
            </li>
          );
        })}
        {audit.length === 0 && <li className="pulse px-4 py-3 text-[12.5px] text-ink-3">Loading trace…</li>}
        {waiting && (
          <li className="grid grid-cols-[52px_72px_1fr] gap-2 px-4 py-2 text-[12.5px]"><span /><span className="font-medium text-amber">Policy</span><span className="pulse text-ink-3">awaiting approval…</span></li>
        )}
      </ol>
    </div>
  );
}
