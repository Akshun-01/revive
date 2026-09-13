"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw, ShieldAlert } from "lucide-react";
import type { Approval } from "@/lib/types";
import { client } from "@/lib/api";
import { ACTION_LABEL } from "@/lib/labels";
import { Button, Empty, Skeleton } from "./ui";

type LoadState = { kind: "loading" } | { kind: "ready"; items: Approval[] } | { kind: "error"; message: string };

export function ApprovalsInbox() {
  const router = useRouter();
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setState({ kind: "ready", items: await client.listApprovals() }); }
    catch (e) { setState({ kind: "error", message: e instanceof Error ? e.message : String(e) }); }
  }, []);

  useEffect(() => {
    let alive = true;
    client.listApprovals()
      .then((items) => { if (alive) setState({ kind: "ready", items }); })
      .catch((e) => { if (alive) setState({ kind: "error", message: e instanceof Error ? e.message : String(e) }); });
    return () => { alive = false; };
  }, []);

  async function act(a: Approval, approve: boolean) {
    setBusy(a.investigation_id);
    try {
      if (approve) await client.approve(a.investigation_id);
      else await client.reject(a.investigation_id, "Rejected from approvals inbox");
      await load();
    } catch (e) {
      setState({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    } finally {
      setBusy(null);
    }
  }

  if (state.kind === "loading") return <div className="border border-line bg-surface p-5"><Skeleton lines={3} /></div>;
  if (state.kind === "error") {
    return (
      <div className="border border-red bg-red-bg p-5 text-[13px] text-red">
        <div className="mb-3">Could not load approvals: {state.message}</div>
        <Button variant="secondary" className="h-8" onClick={load}><RefreshCw size={13} /> Retry</Button>
      </div>
    );
  }
  if (state.items.length === 0) {
    return <div className="border border-line bg-surface p-8"><Empty>No pending approvals. Nothing is waiting on you.</Empty></div>;
  }

  return (
    <div className="flex flex-col gap-3">
      {state.items.map((a) => {
        const p = a.pending_action.parameters as { to?: string; subject?: string };
        const pending = busy === a.investigation_id;
        return (
          <div key={a.investigation_id} className="border-2 border-amber bg-surface">
            <div className="flex items-center gap-2 border-b border-amber bg-amber-bg px-5 py-2.5 text-amber">
              <ShieldAlert size={15} />
              <span className="micro !text-amber">Approval required · external communication</span>
              <span className="ml-auto text-[12.5px] font-medium">{a.customer ?? a.investigation_id}</span>
            </div>
            <div className="flex flex-wrap items-center gap-4 p-5">
              <div className="min-w-0">
                <div className="text-[14px] font-medium">{ACTION_LABEL[a.pending_action.type]}</div>
                <div className="text-[12.5px] text-ink-2">{a.pending_action.description}</div>
                {p.to && <div className="mt-1 text-[12px] text-ink-3">To <span className="num">{p.to}</span>{p.subject ? ` · ${p.subject}` : ""}</div>}
              </div>
              <div className="ml-auto flex gap-2">
                <Button variant="secondary" className="h-8" onClick={() => router.push(`/investigations/${a.investigation_id}`)}>Review &amp; edit</Button>
                <Button className="h-8" disabled={pending} onClick={() => act(a, true)}>Approve &amp; send</Button>
                <Button variant="danger" className="h-8" disabled={pending} onClick={() => act(a, false)}>Reject</Button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
