"use client";

import { Fragment, useState } from "react";

type Series = { id: string; name: string };
type Group = { key: string; name: string; series: Series[]; fiscal?: boolean };

// Series-to-group mapping read from Spec_US_new.xlsx / Spec_US_fiscal.xlsx (Model == 1).
// 28 macro series in 8 groups, common to both models; the fiscal block (3 series) is added
// only to the Fiscal-enhanced DFM.
const MACRO_GROUPS: Group[] = [
  {
    key: "labor",
    name: "Labor",
    series: [
      { id: "PAYEMS", name: "Payroll employment" },
      { id: "JTSJOL", name: "Job openings" },
      { id: "UNRATE", name: "Unemployment rate" },
      { id: "ULCNFB", name: "Unit labor cost" },
    ],
  },
  {
    key: "na",
    name: "National Accounts",
    series: [
      { id: "GDPC1", name: "Real gross domestic product" },
      { id: "DSPIC96", name: "Personal income" },
    ],
  },
  {
    key: "prices",
    name: "Prices",
    series: [
      { id: "CPIAUCSL", name: "Consumer Price Index" },
      { id: "CPILFESL", name: "Core Consumer Price Index" },
      { id: "PCEPILFE", name: "Core PCE Price Index" },
      { id: "PCEPI", name: "PCE Price Index" },
    ],
  },
  {
    key: "mfg",
    name: "Manufacturing",
    series: [
      { id: "DGORDER", name: "Durable goods orders" },
      { id: "INDPRO", name: "Industrial production" },
      { id: "TCU", name: "Capacity utilization rate" },
      { id: "AMDMVS", name: "Durable goods shipments" },
      { id: "AMDMUO", name: "Unfilled orders, all industries" },
      { id: "AMDMTI", name: "Durable goods inventories" },
    ],
  },
  {
    key: "retail",
    name: "Retail & Consumption",
    series: [
      { id: "RSAFS", name: "Retail sales" },
      { id: "PCEC96", name: "Real consumption spending" },
    ],
  },
  {
    key: "housing",
    name: "Housing & Construction",
    series: [
      { id: "HOUST", name: "Housing starts" },
      { id: "TTLCONS", name: "Construction spending" },
      { id: "PERMIT", name: "Building permits" },
    ],
  },
  {
    key: "trade",
    name: "International Trade",
    series: [
      { id: "BOPTEXP", name: "Exports" },
      { id: "BOPTIMP", name: "Imports" },
      { id: "IR", name: "Import price index" },
      { id: "BUSINV", name: "Business inventories" },
      { id: "IQ", name: "Export price index" },
    ],
  },
  {
    key: "surveys",
    name: "Surveys",
    series: [
      { id: "GACDISA066MSFRBNY", name: "Empire State manufacturing index" },
      { id: "GACDFSA066MSFRBPHI", name: "Philadelphia Fed manufacturing index" },
    ],
  },
];

const FISCAL_GROUP: Group = {
  key: "fiscal",
  name: "Fiscal block",
  fiscal: true,
  series: [
    { id: "MTSDS133FMS", name: "Federal surplus or deficit" },
    { id: "GCEC1", name: "Government consumption and investment" },
    { id: "W875RX1", name: "Real income excluding transfers" },
  ],
};

export function VariablesSection() {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const groups = [...MACRO_GROUPS, FISCAL_GROUP];
  const toggle = (key: string) => setOpen((o) => ({ ...o, [key]: !o[key] }));

  return (
    <div className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
            <th className="py-2 pr-3 font-medium">Variable group</th>
            <th className="px-3 py-2 text-center font-medium">Staff Nowcast</th>
            <th className="px-3 py-2 text-center font-medium">Fiscal-enhanced</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((g) => {
            const isOpen = open[g.key] ?? false;
            return (
              <Fragment key={g.key}>
                <tr
                  onClick={() => toggle(g.key)}
                  aria-expanded={isOpen}
                  className={`cursor-pointer border-b border-line/70 transition-colors hover:bg-slate-50 ${
                    g.fiscal ? "bg-pink-50/60 font-medium text-ink" : "text-slate-700"
                  }`}
                >
                  <td className="py-2.5 pr-3">
                    <span className="inline-flex items-center gap-2">
                      <span
                        className={`inline-block text-slate-400 transition-transform ${
                          isOpen ? "rotate-90" : ""
                        }`}
                      >
                        &#9656;
                      </span>
                      <span>{g.name}</span>
                      <span className="font-mono text-xs text-slate-400">{g.series.length}</span>
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    {g.fiscal ? (
                      <span className="text-slate-300">&mdash;</span>
                    ) : (
                      <span className="text-baseline">&#10003;</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-center text-fiscal">&#10003;</td>
                </tr>
                {isOpen ? (
                  <tr className={g.fiscal ? "bg-pink-50/30" : "bg-slate-50/70"}>
                    <td colSpan={3} className="px-3 pb-3 pt-1 text-left">
                      <ul className="space-y-1 pl-6">
                        {g.series.map((s) => (
                          <li key={s.id} className="text-left text-xs">
                            <span className="text-slate-600">{s.name}</span>
                            <span className="ml-2 font-mono text-slate-400">{s.id}</span>
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            );
          })}
        </tbody>
      </table>
      <p className="mt-3 border-t border-line pt-3 text-xs text-slate-500">
        Click a group to list its series. The 28 macro series are common to both models; the
        Fiscal-enhanced DFM adds the three-series fiscal block (federal deficit, government spending,
        income excluding transfers).
      </p>
    </div>
  );
}
