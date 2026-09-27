import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RetryProof — Prove the fix. Don't trust the agent.",
  description:
    "RetryProof reproduces retry failures and reruns the exact same frozen contract after IBM Bob repairs the application.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
