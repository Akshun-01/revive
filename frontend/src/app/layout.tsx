import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { BackendStatus } from "@/components/BackendStatus";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Revive",
  description: "Revenue recovery agent: investigate why a customer didn't renew, decide if recovery is rational, act, verify.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full`} suppressHydrationWarning>
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        <header className="border-b border-line bg-surface">
          <div className="mx-auto flex h-12 max-w-[1440px] items-center justify-between gap-6 px-6">
            <Link href="/" className="flex items-center gap-3">
              <span className="inline-block h-3 w-3 bg-ink" aria-hidden />
              <span className="text-[15px] font-semibold tracking-tight">Revive</span>
              <span className="micro hidden sm:inline">Revenue recovery agent</span>
            </Link>
            <nav className="flex items-center gap-6 text-[13px] text-ink-2">
              <Link href="/" className="hover:text-ink">Investigations</Link>
              <Link href="/approvals" className="hover:text-ink">Approvals</Link>
              <Link href="/settings/integrations" className="hover:text-ink">Integrations</Link>
              <BackendStatus />
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
