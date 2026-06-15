import type { ReactNode } from "react";

export function Section({
  id,
  eyebrow,
  title,
  intro,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  intro?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-line py-12">
      <div className="mx-auto max-w-6xl px-5">
        <p className="eyebrow">{eyebrow}</p>
        <h2 className="section-title mt-1">{title}</h2>
        {intro ? <div className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600">{intro}</div> : null}
        <div className="mt-7">{children}</div>
      </div>
    </section>
  );
}

export function Stat({
  label,
  value,
  unit,
  sub,
  accent,
}: {
  label: string;
  value: string;
  unit?: string;
  sub?: string;
  accent?: "baseline" | "fiscal" | "neutral";
}) {
  const bar =
    accent === "baseline"
      ? "before:bg-baseline"
      : accent === "fiscal"
        ? "before:bg-fiscal"
        : "before:bg-slate-300";
  return (
    <div
      className={`card relative overflow-hidden pl-5 before:absolute before:left-0 before:top-0 before:h-full before:w-1 ${bar}`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 font-mono text-3xl font-semibold tabular-nums text-ink">
        {value}
        {unit ? <span className="ml-1 text-base font-normal text-muted">{unit}</span> : null}
      </p>
      {sub ? <p className="mt-1 text-xs text-slate-500">{sub}</p> : null}
    </div>
  );
}

export function Pill({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "amber" | "blue" | "green" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-600",
    amber: "bg-amber-100 text-amber-700",
    blue: "bg-blue-100 text-blue-700",
    green: "bg-green-100 text-green-700",
  } as const;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

/** Significance badge for a p-value (two-sided, alpha = 0.05). */
export function SigBadge({ p }: { p: number }) {
  const sig = p < 0.05;
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 font-mono text-xs ${
        sig ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"
      }`}
    >
      {sig ? "sig." : "n.s."}
    </span>
  );
}
