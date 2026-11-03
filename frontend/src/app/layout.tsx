import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LinkedIn OSINT & Cohort Discovery Suite",
  description: "Regulated CSV-to-CV pipeline, Cohort X-Ray Shortlister, Public Jobs Guest Harvester, and Voyager HAR Ingest",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
