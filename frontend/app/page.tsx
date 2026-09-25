'use client';

import React from 'react';
import Link from 'next/link';
import {
  ArrowRight,
  ShieldCheck,
  Scale,
  FileText,
  Sparkles,
  UploadCloud,
  CheckCircle2,
  Zap,
  BookOpen,
  Search,
  LayoutDashboard,
  Layers,
} from 'lucide-react';

export default function HomePage() {
  const features = [
    {
      icon: Search,
      title: 'Hybrid Legal Retrieval',
      desc: 'Blends BM25 statutory search with dense neural embeddings for high-precision Indian legal provisions and precedent retrieval.',
      href: '/ask',
      cta: 'Explore Search',
    },
    {
      icon: Scale,
      title: 'Contract & Clause Risk',
      desc: 'Detects indemnity traps, non-compete liabilities, dispute resolution bottlenecks, and compliance deviations.',
      href: '/dashboard',
      cta: 'Analyze Contract',
    },
    {
      icon: ShieldCheck,
      title: 'Evidence-First Grounding',
      desc: 'Zero hallucinated legal statutes. Every single AI output is backed by verifiable citations and statutory provenance.',
      href: '/sources',
      cta: 'View Knowledge Base',
    },
    {
      icon: FileText,
      title: 'Plain Language Summaries',
      desc: 'Translates convoluted Indian legal terminology into actionable plain-language summaries and deadline matrices.',
      href: '/documents',
      cta: 'Browse Documents',
    },
  ];

  const quickStats = [
    { label: 'Statutory Sections & Rules', value: '1,200+' },
    { label: 'Grounding Verification Rate', value: '100%' },
    { label: 'Retrieval Latency', value: '< 180ms' },
    { label: 'Adversarial Prompt Defense', value: 'Active' },
  ];

  return (
    <div className="space-y-12 py-4">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-900 via-indigo-950 to-slate-950 text-white p-8 md:p-12 shadow-xl border border-blue-800/40">
        <div className="absolute top-0 right-0 -mt-12 -mr-12 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-400/30 backdrop-blur-xs">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
            <span>India-First • Evidence-First Legal AI</span>
          </div>

          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight leading-tight text-white">
            Demystify Indian Law with Grounded AI Intelligence
          </h1>

          <p className="text-base md:text-lg text-slate-300 leading-relaxed max-w-2xl">
            Upload contracts, interrogate Indian acts, detect hidden clause risks, and extract obligation timelines — with strict citation provenance and zero legal hallucinations.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm shadow-lg shadow-blue-900/40 transition hover:scale-[1.02]"
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Launch Dashboard</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>

            <Link
              href="/ask"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-white/10 hover:bg-white/15 text-white font-medium text-sm border border-white/20 backdrop-blur-xs transition"
            >
              <Search className="w-4 h-4 text-blue-300" />
              <span>Ask Legal Question</span>
            </Link>

            <Link
              href="/demo"
              className="inline-flex items-center gap-2 px-4 py-3 rounded-xl text-slate-300 hover:text-white font-medium text-sm hover:underline transition"
            >
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span>Interactive Demo</span>
            </Link>
          </div>
        </div>

        {/* Metric Badges */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-10 pt-8 border-t border-white/10">
          {quickStats.map((stat) => (
            <div key={stat.label}>
              <div className="text-xl md:text-2xl font-bold text-white tracking-tight">{stat.value}</div>
              <div className="text-xs text-slate-400 mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Feature Capabilities Grid */}
      <section className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            Core AI Capabilities
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Engineered specifically for Indian jurisprudence, statutory compliance, and commercial contracts.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {features.map((feat) => {
            const Icon = feat.icon;
            return (
              <div
                key={feat.title}
                className="group p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 hover:shadow-md transition flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800 flex items-center justify-center text-blue-600 dark:text-blue-400">
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition">
                    {feat.title}
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                    {feat.desc}
                  </p>
                </div>

                <div className="pt-4 mt-4 border-t border-slate-100 dark:border-slate-800/80">
                  <Link
                    href={feat.href}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                  >
                    <span>{feat.cta}</span>
                    <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Quick Start Callout */}
      <section className="p-8 rounded-2xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-slate-900 dark:text-slate-100 font-bold text-lg">
            <UploadCloud className="w-5 h-5 text-blue-600" />
            <span>Ready to analyze your legal document?</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 max-w-xl">
            Drop your PDF or contract directly on the Dashboard. Get instant clause extraction, risk assessment, and lawyer-ready briefing notes.
          </p>
        </div>

        <Link
          href="/dashboard"
          className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition"
        >
          <span>Open Dashboard</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </section>
    </div>
  );
}
