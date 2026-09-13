"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import type { AuditEvent, InvestigationStatus } from "@/lib/types";
import { streamInvestigation } from "@/lib/api";
import { Timeline } from "./Timeline";
import { Micro } from "./ui";

// Streams a fresh investigation live, then hands off to the full workspace once it completes
// or pauses for approval. The SSE /stream endpoint starts the run and emits investigation_started
// first, so we learn the id from the stream.
export function LiveRun({ customer }: { customer: string }) {
  const router = useRouter();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [id, setId] = useState<string | null>(null);
  const idRef = useRef<string | null>(null);
  const doneRef = useRef(false);

  useEffect(() => {
    if (!customer) { router.replace("/"); return; }
    const stop = streamInvestigation(customer, (name, data) => {
      if (name === "investigation_started") {
        idRef.current = String(data.id ?? "");
        setId(idRef.current || null);
      }
      setEvents((prev) => [...prev, { event_type: name, payload: data, at: new Date().toISOString() }]);
      if (name === "investigation_completed" || name === "approval_required") {
        doneRef.current = true;
        const id = idRef.current;
        if (id) setTimeout(() => router.replace(`/investigations/${id}?customer=${encodeURIComponent(customer)}`), 700);
      }
    }, () => { if (!doneRef.current) setError("Lost the connection to the agent. The investigation may still be running."); });
    return stop;
  }, [customer, router]);

  return (
    <div className="mx-auto max-w-[760px] px-6 py-10">
      <Micro>Investigating</Micro>
      <h1 className="mb-1 mt-2 flex items-center gap-3 text-[28px] font-semibold tracking-tight">
        <Loader2 size={20} className="animate-spin text-ink-3" />{customer}
      </h1>
      <p className="mb-6 text-[14px] text-ink-2">Reading systems, correlating evidence, deciding whether recovery is rational…</p>
      <Timeline audit={events} status={"running" as InvestigationStatus} />
      {error && (
        <div className="mt-4 border border-red bg-red-bg px-4 py-2 text-[13px] text-red">
          {error} {id
            ? <button className="underline" onClick={() => router.replace(`/investigations/${id}`)}>Open investigation</button>
            : <button className="underline" onClick={() => router.replace("/")}>Back</button>}
        </div>
      )}
    </div>
  );
}
