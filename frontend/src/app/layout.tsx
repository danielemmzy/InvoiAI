import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "InvoiAI — AI Financial Operations",
  description: "Connect QuickBooks or Xero. InvoiAI verifies every document, syncs your books, and tells you what needs attention — before you ask.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
