import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GDP Nowcast - Fiscal | Real-time DFM backtest",
  description:
    "Pseudo-real-time backtest of a dynamic factor model nowcasting US GDP growth, with a fiscal-augmented variant and naive benchmarks. Honest, look-ahead-safe evaluation, 2017-2025.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
