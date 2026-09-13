"use client";

import { useState, type FormEvent } from "react";
import { Loader2, Plug, Unplug } from "lucide-react";
import type { Connection } from "@/lib/types";
import type { ProviderConfig } from "@/lib/providers";
import { shortDate } from "@/lib/labels";
import { Button, Micro, SourceMark, Tag } from "./ui";

type Mode = "idle" | "form" | "confirm-disconnect";

export function ConnectionCard({ provider, connection, onConnect, onDisconnect }: {
  provider: ProviderConfig;
  connection: Connection | null;
  onConnect: (credentials: Record<string, string>) => Promise<void>;
  onDisconnect: () => Promise<void>;
}) {
  const [mode, setMode] = useState<Mode>("idle");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const connected = connection !== null;

  function reset() { setMode("idle"); setToken(""); setError(null); }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const value = token.trim();
    if (!value || busy) return;
    setBusy(true); setError(null);
    try {
      await onConnect({ [provider.credentialKey]: value });
      reset();
    } catch (err) {
      setError(friendly(err));
    } finally {
      setToken(""); // never keep the secret around after submit
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true); setError(null);
    try { await onDisconnect(); reset(); }
    catch (err) { setError(friendly(err)); }
    finally { setBusy(false); }
  }

  const formatOk = token.trim() === "" || token.trim().startsWith(provider.prefixHint);

  return (
    <section className="border border-line bg-surface">
      <div className="flex items-center gap-3 border-b border-line px-5 py-3">
        <SourceMark source={provider.id} size={16} />
        <span className="text-[14px] font-medium">{provider.name}</span>
        <span className="micro hidden sm:inline">{provider.role}</span>
        <span className="ml-auto">
          {connected ? <Tag tone="green">Connected</Tag> : <Tag>Not connected</Tag>}
        </span>
      </div>

      <div className="p-5">
        {mode === "idle" && (
          <div className="flex flex-wrap items-center gap-4">
            {connected ? (
              <>
                <div className="text-[12.5px] text-ink-2">
                  Connected since <span className="num">{shortDate(connection.created_at)}</span>
                  {connection.updated_at !== connection.created_at && <> · updated <span className="num">{shortDate(connection.updated_at)}</span></>}
                  {connection.scopes.length > 0 && <> · scopes <span className="num">{connection.scopes.join(", ")}</span></>}
                </div>
                <div className="ml-auto flex gap-2">
                  <Button variant="secondary" className="h-8" onClick={() => setMode("form")}>Update token</Button>
                  <Button variant="danger" className="h-8" onClick={() => setMode("confirm-disconnect")}><Unplug size={13} /> Disconnect</Button>
                </div>
              </>
            ) : (
              <>
                <div className="text-[12.5px] text-ink-2">Paste a token to let Revive read this system. {provider.help}.</div>
                <Button className="ml-auto h-8" onClick={() => setMode("form")}><Plug size={13} /> Connect</Button>
              </>
            )}
          </div>
        )}

        {mode === "form" && (
          <form onSubmit={submit} className="flex flex-col gap-3">
            <label className="flex flex-col gap-1.5">
              <Micro>{provider.fieldLabel}</Micro>
              <input type="password" autoComplete="off" spellCheck={false} value={token} onChange={(e) => setToken(e.target.value)}
                placeholder={provider.placeholder} autoFocus
                className="h-10 border border-line-2 bg-surface px-3 font-mono text-[13px] outline-none placeholder:text-ink-3 focus:border-ink" />
            </label>
            <div className="flex flex-wrap items-center gap-3 text-[12px] text-ink-3">
              <span>{provider.help}. Sent once to the backend, never stored in this browser.</span>
              {!formatOk && <span className="text-amber">Expected to start with {provider.prefixHint}</span>}
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={busy || !token.trim()} className="h-8">
                {busy ? <Loader2 size={13} className="animate-spin" /> : <Plug size={13} />}
                {connected ? "Update token" : "Connect"}
              </Button>
              <Button type="button" variant="secondary" className="h-8" onClick={reset} disabled={busy}>Cancel</Button>
            </div>
          </form>
        )}

        {mode === "confirm-disconnect" && (
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[13px]">Disconnect {provider.name}? Investigations will run without this evidence source.</span>
            <div className="ml-auto flex gap-2">
              <Button variant="danger" className="h-8" onClick={disconnect} disabled={busy}>
                {busy ? <Loader2 size={13} className="animate-spin" /> : <Unplug size={13} />} Confirm disconnect
              </Button>
              <Button variant="secondary" className="h-8" onClick={reset} disabled={busy}>Cancel</Button>
            </div>
          </div>
        )}

        {error && <div className="mt-3 border border-red bg-red-bg px-3 py-2 text-[12.5px] text-red">{error}</div>}
      </div>
    </section>
  );
}

function friendly(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err);
  if (/^400\b/.test(msg)) return "Integration is temporarily unavailable, try again later.";
  if (/Failed to fetch|NetworkError|Load failed/i.test(msg)) return "Could not reach the backend. Check the connection and try again.";
  return msg;
}
