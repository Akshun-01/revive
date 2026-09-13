"use client";

import clsx from "clsx";
import { Check, X, AlertTriangle, ExternalLink } from "lucide-react";
import type {
  Action, CauseHypothesis, Diagnosis, Evidence, EvidenceSource, Intervention, RecoverabilityDecision, VerificationResult,
} from "@/lib/types";
import { ACTION_LABEL, CAUSE_LABEL, INTERVENTION_LABEL, RECOVERABILITY_LABEL, SOURCE_LABEL, SOURCE_ROLE, clock, pct, shortDate } from "@/lib/labels";
import { Empty, Meter, Micro, Panel, Skeleton, SourceMark, Tag, type Tone } from "./ui";

// ---------------------------------------------------------------- shared

export type Highlight = { ids: Set<string>; set: (ids: string[] | null) => void; jump: (id: string) => void };

export function EvidenceChips({ ids, hl, tone = "neutral" }: { ids: string[]; hl: Highlight; tone?: Tone }) {
  if (!ids.length) return <span className="text-[12px] text-ink-3">none</span>;
  return (
    <span className="inline-flex flex-wrap gap-1">
      {ids.map((id) => (
        <button key={id} type="button" onMouseEnter={() => hl.set([id])} onMouseLeave={() => hl.set(null)} onClick={() => hl.jump(id)}
          className={clsx("num border px-1 text-[10.5px] hover:border-ink hover:bg-surface-2", tone === "red" ? "border-red text-red" : "border-line-2 text-ink-2")}>
          {id}
        </button>
      ))}
    </span>
  );
}

const ORDER: EvidenceSource[] = ["stripe", "hubspot", "userlens", "slack"];

// ---------------------------------------------------------------- evidence

export function EvidenceSection({ evidence, hl, loading, sources }: { evidence: Evidence[]; hl: Highlight; loading: boolean; sources?: Record<string, string> }) {
  const grouped = ORDER.map((s) => ({ source: s, items: evidence.filter((e) => e.source === s) }));
  const any = hl.ids.size > 0;
  return (
    <Panel title="Evidence chain" meta={`${evidence.length} items · 4 sources`} id="evidence">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {grouped.map(({ source, items }) => {
          const status = sources?.[source];
          const unavailable = !loading && typeof status === "string" && status.startsWith("error");
          const comingSoon = source === "userlens"; // integration not live yet - shown as coming soon
          return (
          <div key={source} className={clsx("border border-line", comingSoon && "opacity-70")}>
            <div className="flex items-center gap-2 border-b border-line bg-surface-2 px-3 py-2">
              <SourceMark source={source} />
              <span className="text-[12.5px] font-medium">{SOURCE_LABEL[source]}</span>
              <span className="micro">{SOURCE_ROLE[source]}</span>
              {comingSoon && <Tag tone="amber">coming soon</Tag>}
              <span className="ml-auto micro">{comingSoon ? <span className="text-amber">soon</span> : items.length ? `${items.length}` : loading ? <span className="pulse">querying</span> : unavailable ? <span className="text-amber">unavailable</span> : "—"}</span>
            </div>
            <ul className="divide-y divide-line">
              {comingSoon
                ? <li className="p-3 text-[12px] text-ink-3">Product-behavior signals (usage &amp; adoption) — <span className="text-amber">coming soon</span>.</li>
                : items.length === 0 && (loading
                  ? <li className="p-3"><Skeleton lines={2} /></li>
                  : <li className="p-3 text-[12px] text-ink-3">{unavailable ? "Source unavailable for this run." : "No evidence from this source."}</li>)}
              {!comingSoon && items.map((e) => {
                const on = hl.ids.has(e.id);
                return (
                  <li key={e.id} id={`ev-${e.id}`}
                    className={clsx("rise p-3 transition-opacity", on && "evidence-hl", any && !on && "evidence-dim")}>
                    <div className="mb-1 flex items-start justify-between gap-2">
                      <div className="text-[13px] font-medium leading-snug">{e.title}</div>
                      <span className="num shrink-0 text-[10.5px] text-ink-3">{e.id}</span>
                    </div>
                    <p className="text-[12.5px] leading-relaxed text-ink-2">{e.finding}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <span className="micro">conf {pct(e.confidence)}</span>
                      {e.timestamp && <span className="micro">· {shortDate(e.timestamp)}</span>}
                      {e.supports.map((c) => <Tag key={`s${c}`} tone="green">+ {c.replace(/_/g, " ")}</Tag>)}
                      {e.contradicts.map((c) => <Tag key={`c${c}`} tone="red">− {c.replace(/_/g, " ")}</Tag>)}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
          );
        })}
      </div>
    </Panel>
  );
}

// ---------------------------------------------------------------- cause

function Hypothesis({ h, hl, primary }: { h: CauseHypothesis; hl: Highlight; primary?: boolean }) {
  return (
    <div onMouseEnter={() => hl.set([...h.supporting_evidence_ids, ...h.contradicting_evidence_ids])} onMouseLeave={() => hl.set(null)}
      className={clsx("border p-4", primary ? "border-ink" : "border-line")}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {primary ? <Tag tone="ink">Primary cause</Tag> : <Tag>Alternative</Tag>}
          <span className={clsx("font-medium", primary ? "text-[17px] tracking-tight" : "text-[14px]")}>{CAUSE_LABEL[h.category]}</span>
        </div>
        <span className="num text-[13px] text-ink-2">{pct(h.confidence)}</span>
      </div>
      <Meter value={h.confidence} tone={primary ? "ink" : "neutral"} className="mb-3" />
      <p className="text-[13px] leading-relaxed text-ink-2">{h.reasoning}</p>
      <div className="mt-3 grid grid-cols-[92px_1fr] gap-y-1.5 text-[12px]">
        <Micro>Supported by</Micro><EvidenceChips ids={h.supporting_evidence_ids} hl={hl} />
        <Micro>Contradicted</Micro><EvidenceChips ids={h.contradicting_evidence_ids} hl={hl} tone="red" />
      </div>
    </div>
  );
}

export function CauseSection({ diagnosis, hl, warnings }: { diagnosis: Diagnosis | null; hl: Highlight; warnings: string[] }) {
  return (
    <Panel title="Root cause" meta={diagnosis ? `confidence ${pct(diagnosis.confidence)}` : "pending"} id="cause">
      {!diagnosis ? <Skeleton lines={4} /> : (
        <div className="flex flex-col gap-3">
          <Hypothesis h={diagnosis.primary_cause} hl={hl} primary />
          {diagnosis.alternatives.map((a) => <Hypothesis key={a.category} h={a} hl={hl} />)}
          {warnings.map((w) => (
            <div key={w} className="flex items-start gap-2 border border-amber bg-amber-bg px-3 py-2 text-[12.5px] text-amber">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />{w}
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

// ---------------------------------------------------------------- recoverability

export const DECISION_TONE: Record<RecoverabilityDecision["decision"], Tone> = { recoverable: "green", not_recoverable: "red", insufficient_evidence: "amber" };

export function RecoverabilitySection({ r, hl }: { r: RecoverabilityDecision | null; hl: Highlight }) {
  return (
    <Panel title="Recoverability" meta={r ? `confidence ${pct(r.confidence)}` : "pending"} id="recoverability">
      {!r ? <Skeleton lines={4} /> : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-[1fr_220px]">
          <div>
            <div className="mb-2 flex items-center gap-3">
              <Tag tone={DECISION_TONE[r.decision]} className="!text-[12px] !px-2.5 !py-1">{RECOVERABILITY_LABEL[r.decision]}</Tag>
              <span className="text-[13px] text-ink-3">{r.decision.replace(/_/g, " ")}</span>
            </div>
            <p className="text-[13.5px] leading-relaxed">{r.reasoning}</p>
            <div className="mt-3 flex items-center gap-2 text-[12px]"><Micro>Based on</Micro><EvidenceChips ids={r.supporting_evidence_ids} hl={hl} /></div>
          </div>
          <div className="flex flex-col gap-2 border-l border-line pl-5">
            {Object.entries(r.factors).map(([k, v]) => (
              <div key={k}>
                <div className="mb-1 flex justify-between text-[11.5px]"><span className="text-ink-2">{k.replace(/_/g, " ")}</span><span className="num text-ink-3">{pct(v)}</span></div>
                <Meter value={v} tone={v >= 0.7 ? "green" : v <= 0.3 ? "red" : "neutral"} />
              </div>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}

// ---------------------------------------------------------------- intervention

export function InterventionSection({ i, hl }: { i: Intervention | null; hl: Highlight }) {
  return (
    <Panel title="Recommended intervention" meta={i ? `priority ${i.priority}` : "pending"} id="intervention">
      {!i ? <Skeleton lines={3} /> : (
        <div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="text-[17px] font-medium tracking-tight">{INTERVENTION_LABEL[i.type]}</span>
            <Tag tone={i.priority === "high" ? "ink" : "neutral"}>{i.priority}</Tag>
            {i.approval_required ? <Tag tone="amber">approval required</Tag> : <Tag tone="green">internal only</Tag>}
          </div>
          <dl className="grid grid-cols-1 gap-x-8 gap-y-3 text-[13px] md:grid-cols-3">
            <div><Micro className="mb-1">Why</Micro><dd className="leading-relaxed text-ink-2">{i.reason}</dd></div>
            <div><Micro className="mb-1">Expected outcome</Micro><dd className="leading-relaxed text-ink-2">{i.expected_outcome}</dd></div>
            <div><Micro className="mb-1">Risk</Micro><dd className="leading-relaxed text-ink-2">{i.risk}</dd></div>
          </dl>
          <div className="mt-3 flex items-center gap-2 text-[12px]"><Micro>Evidence</Micro><EvidenceChips ids={i.supporting_evidence_ids} hl={hl} /></div>
        </div>
      )}
    </Panel>
  );
}

// ---------------------------------------------------------------- actions + verification

const ACTION_TONE: Record<Action["status"], Tone> = { proposed: "neutral", approved: "blue", rejected: "red", executed: "blue", failed: "red", verified: "green" };

export function ActionsSection({ actions, verification }: { actions: Action[]; verification: VerificationResult[] }) {
  const byId = Object.fromEntries(verification.map((v) => [v.action_id, v]));
  return (
    <Panel title="Actions & verification" meta={actions.length ? `${verification.filter((v) => v.verified).length}/${actions.length} verified` : "pending"} id="actions">
      {!actions.length ? <Empty>No actions proposed yet.</Empty> : (
        <ul className="divide-y divide-line border border-line">
          {actions.map((a) => {
            const v = byId[a.id];
            const skipped = a.status === "rejected" && a.result && !a.approval_required;
            return (
              <li key={a.id} className="grid grid-cols-1 gap-3 p-4 md:grid-cols-[1fr_300px]">
                <div>
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <span className="text-[13.5px] font-medium">{ACTION_LABEL[a.type]}</span>
                    <Tag tone={skipped ? "amber" : ACTION_TONE[a.status]}>{skipped ? "suppressed" : a.status}</Tag>
                    {a.approval_required && <Tag tone="amber">human approval</Tag>}
                  </div>
                  <p className="text-[12.5px] text-ink-2">{a.description}</p>
                  {a.result && (
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px]">
                      <span className={clsx(a.result.success ? "text-ink-2" : "text-amber")}>{a.result.message}</span>
                      {a.result.external_reference && (
                        <span className="num inline-flex items-center gap-1 border border-line px-1 text-[10.5px] text-ink-3"><ExternalLink size={10} />{a.result.external_reference}</span>
                      )}
                      <span className="num text-ink-3">{clock(a.result.executed_at)}</span>
                    </div>
                  )}
                </div>
                <div className="border-l border-line pl-4 text-[12px]">
                  <Micro className="mb-1.5">Verification</Micro>
                  {!v ? (
                    <span className={clsx("text-ink-3", a.status === "executed" && "pulse")}>{a.status === "executed" ? "Reading back from source system…" : "—"}</span>
                  ) : (
                    <div>
                      <div className={clsx("mb-1.5 flex items-center gap-1.5 font-medium", v.verified ? "text-green" : "text-red")}>
                        {v.verified ? <Check size={14} /> : <X size={14} />}{v.verified ? "State confirmed" : "Mismatch"}
                        <span className="num ml-auto font-normal text-ink-3">{clock(v.verified_at)}</span>
                      </div>
                      <div className="grid grid-cols-[64px_1fr] gap-y-0.5 text-[11.5px]">
                        <span className="text-ink-3">expected</span><code className="num truncate text-ink-2">{JSON.stringify(v.expected_state)}</code>
                        <span className="text-ink-3">actual</span><code className="num truncate text-ink-2">{JSON.stringify(v.actual_state)}</code>
                      </div>
                      {v.discrepancies.map((d) => <div key={d} className="mt-1 text-red">{d}</div>)}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}
