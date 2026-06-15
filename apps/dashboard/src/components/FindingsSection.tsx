import { data } from "@/lib/data";

function evidenceChips(evidence: Record<string, unknown>): { k: string; v: string }[] {
  return Object.entries(evidence).map(([k, val]) => {
    let v: string;
    if (Array.isArray(val)) v = val.join(", ");
    else if (typeof val === "number") v = Number.isInteger(val) ? String(val) : val.toFixed(3);
    else v = String(val);
    return { k: k.replace(/_/g, " "), v };
  });
}

export function FindingsSection() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {data.findings.map((f, i) => (
        <div key={f.id} className="card flex flex-col">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white">
              {i + 1}
            </span>
            <h3 className="text-sm font-semibold leading-snug text-ink">{f.title}</h3>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.body}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {evidenceChips(f.evidence).map(({ k, v }) => (
              <span
                key={k}
                className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
              >
                <span className="text-slate-400">{k}</span>
                <span className="font-mono font-medium text-slate-700">{v}</span>
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
