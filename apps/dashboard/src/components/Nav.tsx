const LINKS = [
  { href: "#fiscal", label: "Fiscal vs macro" },
  { href: "#deficit", label: "Deficit signal" },
  { href: "#headline", label: "Accuracy" },
  { href: "#weekly", label: "Weekly path" },
  { href: "#benchmarks", label: "Vs traditional" },
  { href: "#findings", label: "Findings" },
  { href: "#method", label: "Method" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white/85 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
        <a href="#top" className="flex items-center gap-2 text-sm font-semibold text-ink">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-baseline" />
          GDP Nowcast<span className="text-muted">/ fiscal</span>
        </a>
        <ul className="hidden gap-5 text-sm text-slate-600 md:flex">
          {LINKS.map((l) => (
            <li key={l.href}>
              <a className="transition-colors hover:text-ink" href={l.href}>
                {l.label}
              </a>
            </li>
          ))}
        </ul>
        <a
          href="https://github.com/mattecasta17/GDPnowcast-fiscal"
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-slate-300 hover:text-ink"
        >
          Source
        </a>
      </nav>
    </header>
  );
}
