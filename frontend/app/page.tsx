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
  BookOpen,
  Search,
  LayoutDashboard,
  Layers,
  Clock,
  GitCompare,
  Lock,
  Compass,
} from 'lucide-react';

export default function HomePage() {
  const userJourneySteps = [
    {
      num: '01',
      title: 'Upload',
      desc: 'Add your legal contract, employment agreement, or notice in PDF or text format.',
    },
    {
      num: '02',
      title: 'Understand',
      desc: 'Receive an automated structured overview with key sections and legal hierarchy.',
    },
    {
      num: '03',
      title: 'Ask',
      desc: 'Interrogate specific provisions, penalties, or compliance obligations in plain language.',
    },
    {
      num: '04',
      title: 'Analyze',
      desc: 'Evaluate high-risk clauses, indemnities, dispute resolution forums, and milestone dates.',
    },
    {
      num: '05',
      title: 'Verify',
      desc: 'Inspect exact source citations, statute sections, and page references backing every statement.',
    },
    {
      num: '06',
      title: 'Act',
      desc: 'Export a professional lawyer intake dossier or proceed with clear contractual awareness.',
    },
  ];

  const userProblems = [
    {
      problem: 'Lengthy, Dense Documents',
      solution: 'Structured executive summaries extract core obligations without losing legal nuances.',
    },
    {
      problem: 'Buried Termination & Risk Clauses',
      solution: 'Automatic detection of restrictive covenants, indemnity triggers, and liability caps.',
    },
    {
      problem: 'Missed Notice Periods & Timelines',
      solution: 'Dedicated chronological deadline matrix identifying cure periods and expiry milestones.',
    },
    {
      problem: 'Confusing Legal Jargon',
      solution: 'Plain-language simplifications contextualized against applicable Indian laws.',
    },
  ];

  const capabilities = [
    {
      icon: Search,
      title: 'Find the relevant provision',
      desc: 'Search statutory language and semantic concepts to locate exact relevant evidence across acts and agreements.',
      href: '/ask',
      cta: 'Search Provisions',
    },
    {
      icon: Scale,
      title: 'Understand important clauses',
      desc: 'Identify onerous clauses, unilateral termination risks, and enforceability under Indian jurisprudence.',
      href: '/dashboard',
      cta: 'Analyze Clauses',
    },
    {
      icon: Clock,
      title: 'Extract obligations & deadlines',
      desc: 'Surface who owes what obligation and by when, compiling an actionable chronological timeline.',
      href: '/dashboard',
      cta: 'View Timelines',
    },
    {
      icon: FileText,
      title: 'Explain legal language clearly',
      desc: 'Translate convoluted legalese into accessible terms without sacrificing evidence grounding.',
      href: '/documents',
      cta: 'Browse Documents',
    },
  ];

  return (
    <div className="space-y-16 py-4">
      {/* 1. Hero Section */}
      <section
        aria-labelledby="hero-title"
        className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 text-white p-8 sm:p-12 lg:p-16 shadow-2xl border border-blue-900/50"
      >
        <div className="relative z-10 max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-400/30 backdrop-blur-xs">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" aria-hidden="true" />
            <span>LEGAL DOCUMENT INTELLIGENCE</span>
          </div>

          <h1 id="hero-title" className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight leading-tight text-white">
            Understand complex legal documents with evidence you can trace.
          </h1>

          <p className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl font-normal">
            Upload agreements, ask questions, identify obligations and deadlines, compare clauses, and inspect the verified sources behind every answer.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs shadow-lg shadow-blue-900/50 transition hover:scale-[1.02] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              <UploadCloud className="w-4 h-4" aria-hidden="true" />
              <span>Upload a Document</span>
              <ArrowRight className="w-4 h-4 ml-0.5" aria-hidden="true" />
            </Link>

            <Link
              href="/ask"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl bg-white/10 hover:bg-white/15 text-white font-semibold text-xs border border-white/20 backdrop-blur-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              <Search className="w-4 h-4 text-blue-300" aria-hidden="true" />
              <span>Ask a Legal Question</span>
            </Link>

            <Link
              href="/demo"
              className="inline-flex items-center gap-2 px-4 py-3 rounded-xl text-slate-300 hover:text-white font-medium text-xs hover:underline transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              <Sparkles className="w-3.5 h-3.5 text-purple-300" aria-hidden="true" />
              <span>Interactive Demo Flow</span>
            </Link>
          </div>

          {/* Value Badges */}
          <div className="pt-6 border-t border-white/10 flex flex-wrap items-center gap-4 text-xs text-slate-300">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" aria-hidden="true" />
              <span>India-first Jurisprudence</span>
            </div>
            <span className="text-white/20" aria-hidden="true">•</span>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" aria-hidden="true" />
              <span>Evidence-Grounded Answers</span>
            </div>
            <span className="text-white/20" aria-hidden="true">•</span>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" aria-hidden="true" />
              <span>Source Traceable Citations</span>
            </div>
            <span className="text-white/20" aria-hidden="true">•</span>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" aria-hidden="true" />
              <span>Safety-Aware Guardrails</span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Problem → Solution Section ("Why LegalLens?") */}
      <section aria-labelledby="why-legallens-title" className="space-y-6">
        <div className="max-w-2xl">
          <span className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
            Why LegalLens?
          </span>
          <h2 id="why-legallens-title" className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">
            Manual document review is slow, complex, and prone to oversight.
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-2">
            Legal documents are difficult to interpret, search, and compare manually. Important obligations get buried, deadlines are missed, and relevant provisions are spread across acts.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {userProblems.map((item, idx) => (
            <div
              key={idx}
              className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs flex flex-col justify-between"
            >
              <div className="space-y-2">
                <span className="text-[11px] font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider block">
                  The Problem
                </span>
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                  {item.problem}
                </h3>
              </div>

              <div className="pt-3 mt-3 border-t border-slate-100 dark:border-slate-800/80 space-y-1">
                <span className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider block">
                  How LegalLens Helps
                </span>
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  {item.solution}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 3. The Evidence-First Differentiator */}
      <section
        aria-labelledby="evidence-differentiator-title"
        className="p-8 sm:p-10 rounded-3xl bg-blue-50/50 dark:bg-blue-950/20 border border-blue-200/60 dark:border-blue-900/60 space-y-6"
      >
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <span className="text-xs font-bold text-blue-700 dark:text-blue-300 uppercase tracking-wider">
            Our Core Principle
          </span>
          <h2 id="evidence-differentiator-title" className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Every answer is connected to verifiable evidence.
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            Generic AI chatbots invent legal citations. LegalLens enforces strict provenance tracking from explanation down to statutory chapter and paragraph.
          </p>
        </div>

        {/* Visual Provenance Flow */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-4">
          {[
            { step: 'AI Explanation', detail: 'Direct plain-English legal response' },
            { step: 'Claim', detail: 'Factual proposition identified' },
            { step: 'Citation', detail: 'Verifiable statutory reference' },
            { step: 'Section', detail: 'Explicit statutory clause or sub-clause' },
            { step: 'Page', detail: 'Exact document coordinate' },
            { step: 'Source', detail: 'Official Gazette / Judicial Precedent' },
          ].map((node, i) => (
            <div
              key={node.step}
              className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-blue-200 dark:border-blue-900/80 text-center shadow-xs flex flex-col justify-between"
            >
              <div>
                <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider block">
                  Step 0{i + 1}
                </span>
                <span className="text-xs font-bold text-slate-900 dark:text-slate-100 block mt-1">
                  {node.step}
                </span>
              </div>
              <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 block">
                {node.detail}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Complete User Journey */}
      <section aria-labelledby="user-journey-title" className="space-y-6">
        <div>
          <span className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
            User Workflow
          </span>
          <h2 id="user-journey-title" className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">
            From raw document to actionable clarity in 6 steps
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            Follow a structured workflow designed to review legal documents without ambiguity.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {userJourneySteps.map((step) => (
            <div
              key={step.num}
              className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-2 hover:border-blue-300 dark:hover:border-blue-700 transition"
            >
              <span className="text-lg font-extrabold text-blue-600 dark:text-blue-400 block font-mono">
                {step.num}
              </span>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {step.title}
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* 5. Feature Presentation (User Problems Solved) */}
      <section aria-labelledby="features-title" className="space-y-6">
        <div>
          <span className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
            Capabilities
          </span>
          <h2 id="features-title" className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">
            Core features built for Indian commercial practice
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            Engineered specifically for Indian jurisprudence, statutory compliance, and commercial agreements.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {capabilities.map((feat) => {
            const Icon = feat.icon;
            return (
              <div
                key={feat.title}
                className="group p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:shadow-md transition flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800 flex items-center justify-center text-blue-600 dark:text-blue-400">
                    <Icon className="w-5 h-5" aria-hidden="true" />
                  </div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition">
                    {feat.title}
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                    {feat.desc}
                  </p>
                </div>

                <div className="pt-4 mt-4 border-t border-slate-100 dark:border-slate-800/80">
                  <Link
                    href={feat.href}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded p-1"
                  >
                    <span>{feat.cta}</span>
                    <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" aria-hidden="true" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 6. Trust & Safety Section */}
      <section
        aria-labelledby="trust-safety-title"
        className="p-8 sm:p-10 rounded-3xl bg-slate-900 text-white space-y-6 border border-slate-800"
      >
        <div className="max-w-2xl space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
            <span>ETHICAL AI COMPLIANCE</span>
          </div>
          <h2 id="trust-safety-title" className="text-2xl font-bold text-white">
            Built for trustworthy legal information
          </h2>
          <p className="text-xs text-slate-300 leading-relaxed">
            LegalLens operates under clear ethical boundaries, providing grounded legal information to empower legal professionals, enterprises, and citizens.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
          {[
            {
              title: 'Evidence-Backed Answers',
              desc: 'Responses are synthesized exclusively from retrieved statutory provisions and uploaded agreements.',
            },
            {
              title: 'Source Traceability',
              desc: 'Every claim is paired with clickable citations indicating exact sections, pages, and document IDs.',
            },
            {
              title: 'Prompt-Injection Defense',
              desc: 'Multi-layer guardrails isolate user document contents to prevent prompt instruction overrides.',
            },
            {
              title: 'Reference-Data Labelling',
              desc: 'Synthetic and benchmark datasets are transparently identified as reference sources.',
            },
            {
              title: 'Citation Validation',
              desc: 'Automated grounding checks verify that quoted excerpts exist verbatim in source records.',
            },
            {
              title: 'Professional-Review Boundary',
              desc: 'Legal information, not a substitute for professional legal advice. Includes 1-click lawyer dossier export.',
            },
          ].map((item) => (
            <div key={item.title} className="p-4 rounded-xl bg-slate-800/80 border border-slate-700/60 space-y-1.5">
              <h3 className="text-xs font-bold text-white">{item.title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 7. Bottom Quick Launch CTA */}
      <section
        aria-labelledby="cta-bottom-title"
        className="p-8 sm:p-10 rounded-3xl bg-gradient-to-r from-blue-600 to-indigo-700 text-white flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl"
      >
        <div className="space-y-2 text-center md:text-left">
          <h2 id="cta-bottom-title" className="text-xl sm:text-2xl font-bold text-white">
            Ready to review your legal agreements?
          </h2>
          <p className="text-xs sm:text-sm text-blue-100 max-w-xl">
            Upload your agreement on the Dashboard for immediate clause risk analysis, obligation timelines, and citation inspection.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="px-6 py-3 rounded-xl bg-white text-blue-700 hover:bg-blue-50 font-bold text-xs shadow-md transition hover:scale-[1.02] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
          >
            Launch Dashboard
          </Link>
          <Link
            href="/ask"
            className="px-5 py-3 rounded-xl bg-white/10 hover:bg-white/20 text-white font-semibold text-xs border border-white/20 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
          >
            Ask Legal Question
          </Link>
        </div>
      </section>
    </div>
  );
}
