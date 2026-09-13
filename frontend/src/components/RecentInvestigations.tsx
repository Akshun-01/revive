"use client";

import Link from "next/link";
import { useRecentInvestigations } from "@/lib/recent";
import { clock, shortDate } from "@/lib/labels";
import { Empty, Micro } from "./ui";

export function RecentInvestigations() {
  const recent = useRecentInvestigations();
  return (
    <section className="border border-line bg-surface">
      <div className="flex items-center justify-between border-b border-line px-5 py-2.5">
        <Micro className="!text-ink">Recent investigations</Micro>
        <Micro>this browser</Micro>
      </div>
      {recent.length === 0 ? (
        <div className="p-5"><Empty>Nothing yet. Start one above.</Empty></div>
      ) : (
        <ul className="divide-y divide-line">
          {recent.map((r) => (
            <li key={r.id}>
              <Link href={`/investigations/${r.id}?customer=${encodeURIComponent(r.customer)}`}
                className="grid grid-cols-[1fr_auto_auto] items-center gap-4 px-5 py-3 text-[13.5px] hover:bg-surface-2/60">
                <span className="font-medium">{r.customer}</span>
                <span className="num text-[11.5px] text-ink-3">{r.id}</span>
                <span className="num text-[11.5px] text-ink-3">{shortDate(r.started_at)} {clock(r.started_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
