"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, Loader2, RefreshCw } from "lucide-react";
import type { CustomerSummary } from "@/lib/types";
import { client } from "@/lib/api";
import { CAUSE_LABEL, RECOVERABILITY_LABEL, STATUS_LABEL, money, shortDate } from "@/lib/labels";
import { Button, Empty, Kpi, Micro, Skeleton, Tag, type Tone } from "./ui";

type LoadState = { kind: "loading" } | { kind: "ready"; rows: CustomerSummary[] } | { kind: "error"; message: string };

const DECISION_TONE: Record<string, Tone> = { recoverable: "green", not_recoverable: "red", insufficient_evidence: "amber" };
const num = (v: number | string | null) => (v == null ? null : Number(v));

export function LostRenewals() {
  const router = useRouter();
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [busy, setBusy] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let alive = true;
    client.listCustomers()
      .then((rows) => { if (alive) setState({ kind: "ready", rows }); })
      .catch((e) => { if (alive) setState({ kind: "error", message: e instanceof Error ? e.message : String(e) }); });
    return () => { alive = false; };
  }, [reloadKey]);

  function investigate(c: CustomerSummary) {
    setBusy(c.id);
    router.push(`/investigations/live?customer=${encodeURIComponent(c.name)}`);
  }

  if (state.kind === "loading") {
    return <div className="border border-line bg-surface p-5"><Skeleton lines={4} /></div>;
  }
  if (state.kind === "error") {
    return (
      <div className="border border-red bg-red-bg p-5 text-[13px] text-red">
        <div className="mb-3">Could not load accounts: {state.message}</div>
        <Button variant="secondary" className="h-8" onClick={() => setReloadKey((k) => k + 1)}><RefreshCw size={13} /> Retry</Button>
      </div>
    );
  }

  const rows = state.rows;
  const totalArr = rows.reduce((s, r) => s + (num(r.annual_revenue) ?? 0), 0);
  const lost = rows.filter((r) => r.renewal_status === "lost");
  const failed = rows.filter((r) => r.renewal_status === "payment_failed");
  const investigated = rows.filter((r) => r.last_investigation);

  if (rows.length === 0) {
    return (
      <div className="border border-line bg-surface p-8">
        <Empty>
          No lost or at-risk renewals found. Connect Stripe under <Link href="/settings/integrations" className="underline">Integrations</Link> to pull your book of business, or start an investigation by name below.
        </Empty>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 border border-line bg-surface md:grid-cols-4 [&>*+*]:border-l [&>*+*]:border-line">
        <Kpi label="ARR lost" value={money(totalArr)} sub={`${rows.length} account${rows.length === 1 ? "" : "s"}`} tone="red" />
        <Kpi label="Cancelled" value={lost.length} sub={money(lost.reduce((s, r) => s + (num(r.annual_revenue) ?? 0), 0))} />
        <Kpi label="Payment failed" value={failed.length} sub={money(failed.reduce((s, r) => s + (num(r.annual_revenue) ?? 0), 0))} tone="amber" />
        <Kpi label="Investigated" value={investigated.length} sub={`${rows.length - investigated.length} to go`} />
      </div>

      <div className="overflow-x-auto border border-line bg-surface">
        <table className="w-full min-w-[820px] text-[13.5px]">
          <thead>
            <tr className="border-b border-line text-left">
              {["Account", "Owner", "Renewal", "State", "ARR", "Verdict", ""].map((h) => (
                <th key={h} className="micro px-5 py-2.5 font-normal">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => {
              const li = c.last_investigation;
              return (
                <tr key={c.id} className="border-b border-line last:border-b-0 hover:bg-surface-2/60">
                  <td className="px-5 py-3">
                    <div className="font-medium">{c.name}</div>
                    <div className="num text-[11.5px] text-ink-3">{c.id} · {c.source}</div>
                  </td>
                  <td className="px-5 py-3 text-ink-2">{c.owner_name ?? "—"}</td>
                  <td className="num px-5 py-3 text-ink-2">{shortDate(c.renewal_date)}</td>
                  <td className="px-5 py-3">
                    {c.renewal_status === "payment_failed" ? <Tag tone="amber">Payment failed</Tag> : <Tag tone="red">Cancelled</Tag>}
                  </td>
                  <td className="num px-5 py-3 text-right font-medium">{money(num(c.annual_revenue), c.currency ?? "USD")}</td>
                  <td className="px-5 py-3">
                    {li ? (
                      <div className="flex flex-col gap-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          {li.recoverability
                            ? <Tag tone={DECISION_TONE[li.recoverability] ?? "neutral"}>{RECOVERABILITY_LABEL[li.recoverability]}</Tag>
                            : <Tag tone={li.status === "waiting_for_approval" ? "amber" : "neutral"}>{STATUS_LABEL[li.status]}</Tag>}
                        </div>
                        {li.primary_cause && <span className="text-[12px] text-ink-2">{CAUSE_LABEL[li.primary_cause]}</span>}
                      </div>
                    ) : <span className="text-[12px] text-ink-3">Not investigated</span>}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      {li && (
                        <Button variant="secondary" className="h-8" onClick={() => router.push(`/investigations/${li.id}?customer=${encodeURIComponent(c.name)}`)}>
                          {li.status === "waiting_for_approval" ? "Review approval" : "Open"}
                        </Button>
                      )}
                      <Button variant={li ? "secondary" : "primary"} className="h-8" onClick={() => investigate(c)} disabled={busy !== null}>
                        {busy === c.id ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                        {li ? "Re-run" : "Investigate"}
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Micro>Accounts come from the backend: seed fixtures in seed mode, Stripe subscriptions that cancelled or failed to pay in live mode.</Micro>
    </div>
  );
}
