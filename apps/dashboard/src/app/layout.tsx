import type { Metadata } from "next";
import "./globals.css";

const TITLE = "Fiscal-enhanced GDP nowcast | Does fiscal data help?";
const DESCRIPTION =
  "A fiscal-enhanced dynamic factor model vs a macro-only Staff Nowcast for US GDP growth: does adding a fiscal block sharpen the real-time nowcast? Honest, look-ahead-safe pseudo-real-time backtest, 2017-2025.";

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
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
