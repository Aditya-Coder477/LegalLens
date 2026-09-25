import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AppShell } from '../components/layout/AppShell';
import { ThemeProvider } from '../lib/context/ThemeContext';

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
    <html lang="en" suppressHydrationWarning>
      <body className="bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased transition-colors">
        <ThemeProvider>
          <AppShell>{children}</AppShell>
        </ThemeProvider>
      </body>
    </html>
  );
}
