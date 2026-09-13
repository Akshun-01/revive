"use client";

import { useState } from "react";
import { ShieldAlert } from "lucide-react";
import type { Action } from "@/lib/types";
import { client } from "@/lib/api";
import { Button, Micro } from "./ui";

export function ApprovalPanel({ action, investigationId, onDone }: { action: Action; investigationId: string; onDone: () => void }) {
  const p = action.parameters as { to?: string; subject?: string; body?: string };
  const [body, setBody] = useState(p.body ?? "");
  const [reason, setReason] = useState("");
  const [rejecting, setRejecting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // The approval is keyed by investigation_id; edits are keyed by the action id.
  async function approve() {
    setBusy(true); setErr(null);
    try {
      await client.approve(investigationId, body !== p.body ? { [action.id]: { body } } : undefined);
      onDone();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  async function reject() {
    setBusy(true); setErr(null);
    try {
      await client.reject(investigationId, reason || "Rejected by operator");
      onDone();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  return (
    <div className="rise mb-5 border-2 border-amber bg-surface">
      <div className="flex items-center gap-2 border-b border-amber bg-amber-bg px-5 py-2.5 text-amber">
        <ShieldAlert size={15} />
        <span className="micro !text-amber">Approval required · external communication</span>
        <span className="ml-auto text-[12px]">The agent will not contact the customer without you.</span>
      </div>
      <div className="grid grid-cols-1 gap-5 p-5 md:grid-cols-[1fr_280px]">
        <div>
          <div className="mb-3 text-[14px] font-medium">{action.description}</div>
          <div className="mb-2 grid grid-cols-[64px_1fr] gap-y-1 text-[12.5px]">
            <Micro>To</Micro><span className="num">{p.to}</span>
            <Micro>Subject</Micro><span>{p.subject}</span>
          </div>
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={9}
            className="w-full resize-y border border-line-2 bg-surface p-3 font-mono text-[12.5px] leading-relaxed outline-none focus:border-ink" />
          <div className="mt-1 text-[11.5px] text-ink-3">Edit the draft before approving. Edits are sent as <code className="num">edits</code>.</div>
        </div>
        <div className="flex flex-col gap-2 border-l border-line pl-5">
          <Micro className="mb-1">Risk</Micro>
          <p className="mb-3 text-[12.5px] text-ink-2">External message on behalf of the account owner. Reversible only by follow-up.</p>
          {!rejecting ? (
            <>
              <Button onClick={approve} disabled={busy}>Approve &amp; send</Button>
              <Button variant="secondary" onClick={() => setRejecting(true)} disabled={busy}>Reject</Button>
            </>
          ) : (
            <>
              <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (recorded in the trace)"
                className="h-9 border border-line-2 px-3 text-[12.5px] outline-none focus:border-ink" />
              <Button variant="danger" onClick={reject} disabled={busy}>Confirm reject</Button>
              <Button variant="secondary" onClick={() => setRejecting(false)} disabled={busy}>Back</Button>
            </>
          )}
          {err && <div className="text-[12px] text-red">{err}</div>}
        </div>
      </div>
    </div>
  );
}
