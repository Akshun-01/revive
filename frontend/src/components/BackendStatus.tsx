"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { client } from "@/lib/api";

type State = { ok: true; label: string } | { ok: false } | null;

export function BackendStatus() {
  const [state, setState] = useState<State>(null);
  useEffect(() => {
    let alive = true;
    client.health()
      .then((h) => { if (alive) setState({ ok: true, label: [h.data_source, h.llm_provider].filter(Boolean).join(" · ") || "connected" }); })
      .catch(() => { if (alive) setState({ ok: false }); });
    return () => { alive = false; };
  }, []);
  return (
    <span className="micro flex items-center gap-2" title="Backend health">
      <span className={clsx("inline-block h-1.5 w-1.5", state === null ? "bg-line-2" : state.ok ? "bg-green" : "bg-red")} />
      {state === null ? "connecting" : state.ok ? state.label : "backend unreachable"}
    </span>
  );
}
