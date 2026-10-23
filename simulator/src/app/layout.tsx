import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CareSync — Alexa+ Care Coordination Agent (Simulation)",
  description:
    "Voice-first care coordination turning synthetic hospital discharge plans into an approval-gated, auditable follow-up workflow using FastMCP Streamable HTTP.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen text-slate-900 bg-slate-50 antialiased selection:bg-indigo-100 selection:text-indigo-900">
        {children}
      </body>
    </html>
  );
}
