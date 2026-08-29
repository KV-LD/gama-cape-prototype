import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GAMA CAPE",
  description: "G.A.Menon Academy Capability Assessment & Proficiency Engine",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
