"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";

/**
 * Measures its own width and renders the chart with an explicit numeric width/height.
 *
 * Recharts' own ``ResponsiveContainer`` renders a correctly-sized wrapper but fails to draw the
 * chart surface in this Next 15 + React 18.3 + Recharts 2.12 setup (blank, no error). Passing
 * explicit dimensions to the chart sidesteps that entirely and is fully reliable.
 */
export function ChartFrame({
  height,
  children,
}: {
  height: number;
  children: (width: number) => ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setWidth(el.clientWidth);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div ref={ref} style={{ width: "100%", height }}>
      {width > 0 ? children(width) : null}
    </div>
  );
}
