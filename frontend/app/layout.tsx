import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AppShell } from '../components/layout/AppShell';

export const metadata: Metadata = {
  title: 'LegalLens — Evidence-First Legal Intelligence Platform',
  description: 'India-first, evidence-first GenAI legal information workspace.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 antialiased text-slate-900">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
