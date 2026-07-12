import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "NIRMIQ Academic Intelligence",
  description: "ChatGPT-like local study intelligence for grounded documents, citations, papers, and exams",
  icons: {
    icon: "/brand/nirmiq-ais-mark.svg",
    apple: "/brand/nirmiq-ais-mark.svg",
  },
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
