import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "NIRMIQ Academic Intelligence",
  description: "Local-first document research, citation, paper, and exam workspace",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
