import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Candidate Screener | Technical Interview Platform",
  description:
    "AI-powered technical interview platform that adapts to your resume and skills. Upload your resume, choose a role, and get interviewed by an intelligent screening system.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div style={{ position: "relative", zIndex: 1 }}>{children}</div>
      </body>
    </html>
  );
}
