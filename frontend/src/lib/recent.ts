// Recent investigations started from this browser. Client-side convenience only; the backend is the source of truth.

import { useSyncExternalStore } from "react";

export interface RecentInvestigation {
  id: string;
  customer: string;
  started_at: string;
}

const KEY = "revive:recent";
const MAX = 12;
const listeners = new Set<() => void>();
let cache: RecentInvestigation[] | null = null;
const EMPTY: RecentInvestigation[] = [];

function load(): RecentInvestigation[] {
  if (cache) return cache;
  try { cache = JSON.parse(localStorage.getItem(KEY) ?? "[]") as RecentInvestigation[]; } catch { cache = []; }
  return cache;
}

export function rememberInvestigation(entry: RecentInvestigation): void {
  const next = [entry, ...load().filter((r) => r.id !== entry.id)].slice(0, MAX);
  cache = next;
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* storage unavailable */ }
  listeners.forEach((l) => l());
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => { listeners.delete(cb); window.removeEventListener("storage", cb); };
}

export function useRecentInvestigations(): RecentInvestigation[] {
  return useSyncExternalStore(subscribe, load, () => EMPTY);
}
