import type { Metadata } from "next";
import "./globals.css";

const TITLE = "Improving GDP Nowcasting Using Fiscal Variables";
const DESCRIPTION =
  "A fiscal-enhanced dynamic factor model against a macro-only Staff Nowcast for US GDP growth. Look-ahead-safe pseudo-real-time backtest, 2017-2025: the fiscal block improves accuracy outside 2020, and most of the gain traces to federal-deficit news.";

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
