import type { ReactNode } from "react";
import clsx from "clsx";
import type { EvidenceSource } from "@/lib/types";

export function Micro({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("micro", className)}>{children}</div>;
}

export function Panel({ title, meta, children, className, id }: { title: string; meta?: ReactNode; children: ReactNode; className?: string; id?: string }) {
  return (
    <section id={id} className={clsx("border border-line bg-surface", className)}>
      <div className="flex items-center justify-between border-b border-line px-5 py-2.5">
        <h2 className="micro !text-ink">{title}</h2>
        {meta && <div className="micro">{meta}</div>}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

export type Tone = "neutral" | "green" | "red" | "amber" | "blue" | "ink";
const TONE: Record<Tone, string> = {
  neutral: "border-line-2 text-ink-2 bg-surface",
  green: "border-green text-green bg-green-bg",
  red: "border-red text-red bg-red-bg",
  amber: "border-amber text-amber bg-amber-bg",
  blue: "border-blue text-blue bg-blue-bg",
  ink: "border-ink text-surface bg-ink",
};

export function Tag({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 border px-1.5 py-[2px] font-mono text-[10.5px] uppercase tracking-[0.1em]", TONE[tone], className)}>
      {children}
    </span>
  );
}

export function Kpi({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: Tone }) {
  return (
    <div className="flex flex-col gap-1 px-5 py-4">
      <Micro>{label}</Micro>
      <div className={clsx("num text-[26px] font-medium leading-none tracking-tight", tone === "green" && "text-green", tone === "red" && "text-red", tone === "amber" && "text-amber")}>{value}</div>
      {sub && <div className="text-[12px] text-ink-3">{sub}</div>}
    </div>
  );
}

export function Meter({ value, tone = "ink", className }: { value: number; tone?: Tone; className?: string }) {
  const color = tone === "green" ? "bg-green" : tone === "red" ? "bg-red" : tone === "amber" ? "bg-amber" : tone === "blue" ? "bg-blue" : "bg-ink";
  return (
    <div className={clsx("h-1.5 w-full bg-surface-2", className)} role="meter" aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={100}>
      <div className={clsx("h-full", color)} style={{ width: `${Math.max(2, Math.round(value * 100))}%` }} />
    </div>
  );
}

export function Button({ children, variant = "primary", className, ...rest }: { children: ReactNode; variant?: "primary" | "secondary" | "danger" } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base = "inline-flex h-9 items-center justify-center gap-2 border px-4 text-[13px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const v = variant === "primary" ? "border-ink bg-ink text-surface hover:bg-ink-2 hover:border-ink-2"
    : variant === "danger" ? "border-red text-red bg-surface hover:bg-red-bg"
    : "border-line-2 bg-surface text-ink hover:border-ink";
  return <button className={clsx(base, v, className)} {...rest}>{children}</button>;
}

const SOURCE_COLOR: Record<EvidenceSource, string> = {
  stripe: "var(--stripe)", hubspot: "var(--hubspot)", slack: "var(--slack)", userlens: "var(--userlens)",
};
export function SourceMark({ source, size = 14 }: { source: EvidenceSource; size?: number }) {
  return (
    <span aria-hidden className="inline-flex shrink-0 items-center justify-center font-mono font-semibold text-surface"
      style={{ width: size, height: size, fontSize: size * 0.6, background: SOURCE_COLOR[source] }}>
      {source[0].toUpperCase()}
    </span>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="pulse h-3 bg-surface-2" style={{ width: `${90 - i * 18}%` }} />
      ))}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="text-[13px] text-ink-3">{children}</div>;
}
