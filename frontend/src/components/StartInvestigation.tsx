"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { client } from "@/lib/api";
import { rememberInvestigation } from "@/lib/recent";
import { Button, Micro } from "./ui";

export function StartInvestigation() {
  const router = useRouter();
  const [customer, setCustomer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const name = customer.trim();
    if (!name || busy) return;
    setBusy(true); setError(null);
    try {
      const res = await client.startInvestigation(name);
      rememberInvestigation({ id: res.id, customer: res.customer?.name ?? name, started_at: new Date().toISOString() });
      router.push(`/investigations/${res.id}?customer=${encodeURIComponent(res.customer?.name ?? name)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="border border-line bg-surface">
      <div className="border-b border-line px-5 py-2.5"><Micro className="!text-ink">Start an investigation</Micro></div>
      <div className="flex flex-col gap-3 p-5 sm:flex-row sm:items-end">
        <label className="flex flex-1 flex-col gap-1.5">
          <Micro>Customer</Micro>
          <input value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder="Company name as it appears in your CRM" autoFocus
            className="h-10 border border-line-2 bg-surface px-3 text-[14px] outline-none placeholder:text-ink-3 focus:border-ink" />
        </label>
        <Button type="submit" disabled={busy || !customer.trim()} className="h-10">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
          Investigate
        </Button>
      </div>
      {error && <div className="border-t border-red bg-red-bg px-5 py-2 text-[12.5px] text-red">{error}</div>}
    </form>
  );
}
