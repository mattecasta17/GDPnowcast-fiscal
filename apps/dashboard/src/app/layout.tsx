import type { Metadata } from "next";
import "./globals.css";

const TITLE = "GDP Nowcast - Fiscal | Real-time DFM backtest";
const DESCRIPTION =
  "Pseudo-real-time backtest of a dynamic factor model nowcasting US GDP growth, with a fiscal-augmented variant and naive benchmarks. Honest, look-ahead-safe evaluation, 2017-2025.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  openGraph: { title: TITLE, description: DESCRIPTION, type: "website" },
  twitter: { card: "summary", title: TITLE, description: DESCRIPTION },
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
