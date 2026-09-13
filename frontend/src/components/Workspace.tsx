"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import type { Investigation } from "@/lib/types";
import { client } from "@/lib/api";
import { CAUSE_LABEL, INTERVENTION_LABEL, RECOVERABILITY_LABEL, STATUS_LABEL, money, pct, shortDate } from "@/lib/labels";
import { Kpi, Micro, Tag, type Tone } from "./ui";
import { ApprovalPanel } from "./ApprovalPanel";
import { Timeline } from "./Timeline";
import { ActionsSection, CauseSection, EvidenceSection, InterventionSection, RecoverabilitySection, type Highlight } from "./sections";

const DECISION_TEXT: Record<"recoverable" | "not_recoverable" | "insufficient_evidence", string> = { recoverable: "text-green", not_recoverable: "text-red", insufficient_evidence: "text-amber" };

const STATUS_TONE: Record<Investigation["status"], Tone> = {
  created: "neutral", running: "blue", waiting_for_approval: "amber", completed: "green", rejected: "red", failed: "red",
};

export function Workspace({ id, customerHint }: { id: string; customerHint?: string }) {
  const [inv, setInv] = useState<Investigation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hlIds, setHlIds] = useState<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    try { setInv(await client.getInvestigation(id)); setError(null); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }, [id]);

  // Load the investigation. POST /investigations runs synchronously, so by the time we get
  // here it is already completed or waiting_for_approval; the audit[] carries the trace.
  useEffect(() => {
    let cancelled = false;
    client.getInvestigation(id)
      .then((v) => { if (!cancelled) setInv(v); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); });
    return () => { cancelled = true; };
  }, [id]);

  const hl = useMemo<Highlight>(() => ({
    ids: hlIds,
    set: (ids) => setHlIds(new Set(ids ?? [])),
    jump: (evId) => {
      const el = document.getElementById(`ev-${evId}`);
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
    },
  }), [hlIds]);

  const c = inv?.customer;
  const status = inv?.status ?? null;

  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8">
      {/* Header */}
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Micro className="mb-2">Investigation · <span className="num">{id}</span></Micro>
          <h1 className="text-[30px] font-semibold leading-none tracking-tight">{c?.name ?? customerHint ?? "Resolving customer…"}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-[12.5px] text-ink-2">
            {c && <>
              <span className="num">{c.id}</span>
              <span>Owner {c.owner_name ?? "—"}</span>
              <span>Renewal {shortDate(c.renewal_date)}</span>
              <span className="text-ink-3">Stripe {c.external_ids.stripe} · HubSpot {c.external_ids.hubspot}</span>
            </>}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {status && <Tag tone={STATUS_TONE[status]} className="!px-2.5 !py-1 !text-[11.5px]">{STATUS_LABEL[status]}</Tag>}
          {error && <span className="text-[12px] text-red">{error}</span>}
        </div>
      </div>

      {/* Verdict strip */}
      <div className="mb-5 grid grid-cols-2 border border-line bg-surface md:grid-cols-4 [&>*+*]:border-l [&>*+*]:border-line">
        <Kpi label="Revenue lost" value={inv?.revenue_impact != null ? money(inv.revenue_impact) : <span className="pulse text-ink-3">—</span>} sub={c?.renewal_status ? `renewal ${c.renewal_status.replace(/_/g, " ")}` : undefined} tone="red" />
        <Kpi label="Primary cause" value={inv?.diagnosis ? <span className="text-[18px]">{CAUSE_LABEL[inv.diagnosis.primary_cause.category]}</span> : <span className="pulse text-ink-3">—</span>} sub={inv?.diagnosis ? `${pct(inv.diagnosis.confidence)} confidence` : "correlating evidence"} />
        <Kpi label="Recoverability" value={inv?.recoverability ? <span className={clsx("text-[18px]", DECISION_TEXT[inv.recoverability.decision])}>{RECOVERABILITY_LABEL[inv.recoverability.decision]}</span> : <span className="pulse text-ink-3">—</span>} sub={inv?.recoverability ? `${pct(inv.recoverability.confidence)} confidence` : "pending"} />
        <Kpi label="Intervention" value={inv?.intervention ? <span className="text-[18px]">{INTERVENTION_LABEL[inv.intervention.type]}</span> : <span className="pulse text-ink-3">—</span>} sub={inv?.intervention ? `${inv.actions.filter((a) => a.status === "verified").length} of ${inv.actions.length} actions verified` : "pending"} />
      </div>

      {inv?.pending_action && <ApprovalPanel action={inv.pending_action} investigationId={inv.id} onDone={refresh} />}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[300px_1fr]">
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <Timeline audit={inv?.audit ?? []} status={status} />
        </aside>
        <div className="flex min-w-0 flex-col gap-5">
          <EvidenceSection evidence={inv?.evidence ?? []} hl={hl} loading={inv === null} sources={inv?.evidence_sources} />
          <CauseSection diagnosis={inv?.diagnosis ?? null} hl={hl} warnings={inv?.warnings ?? []} />
          <RecoverabilitySection r={inv?.recoverability ?? null} hl={hl} />
          <InterventionSection i={inv?.intervention ?? null} hl={hl} />
          <ActionsSection actions={inv?.actions ?? []} verification={inv?.verification ?? []} />
        </div>
      </div>
    </div>
  );
}
