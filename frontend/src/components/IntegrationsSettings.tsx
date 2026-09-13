"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import type { Connection, Provider } from "@/lib/types";
import { client } from "@/lib/api";
import { PROVIDERS } from "@/lib/providers";
import { Button, Skeleton } from "./ui";
import { ConnectionCard } from "./ConnectionCard";

type LoadState = { kind: "loading" } | { kind: "ready"; connections: Connection[] } | { kind: "error"; message: string };

export function IntegrationsSettings() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  const load = useCallback(async () => {
    try { setState({ kind: "ready", connections: await client.listConnections() }); }
    catch (e) { setState({ kind: "error", message: e instanceof Error ? e.message : String(e) }); }
  }, []);

  useEffect(() => {
    let alive = true;
    client.listConnections()
      .then((connections) => { if (alive) setState({ kind: "ready", connections }); })
      .catch((e) => { if (alive) setState({ kind: "error", message: e instanceof Error ? e.message : String(e) }); });
    return () => { alive = false; };
  }, []);

  async function connect(provider: Provider, credentials: Record<string, string>) {
    await client.connect(provider, credentials);
    await load();
  }
  async function disconnect(provider: Provider) {
    await client.disconnect(provider);
    await load();
  }

  if (state.kind === "loading") {
    return <div className="flex flex-col gap-4">{PROVIDERS.map((p) => <div key={p.id} className="border border-line bg-surface p-5"><Skeleton lines={2} /></div>)}</div>;
  }
  if (state.kind === "error") {
    return (
      <div className="border border-red bg-red-bg p-5 text-[13px] text-red">
        <div className="mb-3">Could not load connections: {state.message}</div>
        <Button variant="secondary" className="h-8" onClick={load}><RefreshCw size={13} /> Retry</Button>
      </div>
    );
  }
  const byProvider = Object.fromEntries(state.connections.map((c) => [c.provider, c])) as Partial<Record<Provider, Connection>>;
  return (
    <div className="flex flex-col gap-4">
      {PROVIDERS.map((p) => (
        <ConnectionCard key={p.id} provider={p} connection={byProvider[p.id] ?? null}
          onConnect={(creds) => connect(p.id, creds)} onDisconnect={() => disconnect(p.id)} />
      ))}
    </div>
  );
}
