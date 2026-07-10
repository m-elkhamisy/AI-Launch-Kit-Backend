import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LaunchKit Generator",
  description: "Turn a client brief into a finished marketing website with Claude, v0, or both.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
