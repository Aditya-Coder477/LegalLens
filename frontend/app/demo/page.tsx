'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  BookOpen,
  ShieldAlert,
  ArrowRight,
  CheckCircle2,
  FileText,
  Search,
  ArrowLeftRight,
  Clock,
  UserCheck,
  Shield,
  Layers,
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import { SourceBadge } from '../../components/citations/SourceBadge';
import { CitationBadge } from '../../components/citations/CitationBadge';
import { SafetyBanner } from '../../components/safety/SafetyBanner';
import { mockSampleAnswer, mockSampleDocument } from '../../fixtures/mockData';
import dynamic from 'next/dynamic';
import { AnswerView } from '../../components/analysis/AnswerView';

const LawyerHandoffModal = dynamic(
  () => import('../../components/analysis/LawyerHandoffModal').then((mod) => mod.LawyerHandoffModal),
  { ssr: false }
);

interface DemoTouchpoint {
  id: number;
  title: string;
  badge: string;
  category: string;
  description: string;
  actionLabel: string;
  linkHref?: string;
  preview: React.ReactNode;
}

export default function DemoWalkthroughPage() {
  const [activeStep, setActiveStep] = useState(1);
  const [handoffOpen, setHandoffOpen] = useState(false);

  const TOUCHPOINTS: DemoTouchpoint[] = [
    {
      id: 1,
      title: 'Evidence-First Legal Q&A with Strict Grounding',
      badge: 'Evaluation Touchpoint #1',
      category: 'Core Q&A',
      description:
        'LegalLens separates AI explanatory text from verified Source Evidence. Every statutory proposition links to a tamper-proof citation with SHA-256 fingerprint.',
      actionLabel: 'Try in Ask LegalLens',
      linkHref: '/ask',
      preview: (
        <div className="space-y-4">
          <AnswerView
            response={mockSampleAnswer}
            onOpenHandoff={() => setHandoffOpen(true)}
          />
        </div>
      ),
    },
    {
      id: 2,
      title: 'Contract Clause Intelligence & Non-Compete Risk',
      badge: 'Evaluation Touchpoint #2',
      category: 'Contract Analysis',
      description:
        'Evaluates restrictive covenants against Section 27 of the Indian Contract Act, 1872. Instantly flags post-employment non-compete clauses as void as a matter of law.',
      actionLabel: 'Analyze Clauses',
      linkHref: `/documents/${mockSampleDocument.document_id}/clauses`,
      preview: (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <span className="text-[10px] font-bold text-red-600 uppercase tracking-wider block">
                High Risk • Enforceability Warning
              </span>
              <h4 className="text-xs font-bold text-slate-900">
                Post-Employment Non-Compete Clause (12 Months, All India)
              </h4>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-red-50 text-red-700 font-semibold border border-red-200">
              Likely Void under S. 27
            </span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            <strong>Statutory Assessment:</strong> Under Section 27 of the Indian Contract Act 1872, every agreement by which anyone is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void. Indian courts do not apply the "reasonableness" test to post-termination restraints.
          </p>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
            <strong>Key Precedent:</strong> <em>Percept D'Mark (India) (P) Ltd. v. Zaheer Khan (2006) 4 SCC 227</em> — The doctrine of restraint of trade applies to contracts of employment only during the term; post-termination restraints are void.
          </div>
        </div>
      ),
    },
    {
      id: 3,
      title: 'Prominent Reference Corpus Disclaimers',
      badge: 'Evaluation Touchpoint #3',
      category: 'Transparency',
      description:
        'Reference benchmark corpora generated for development & RAG benchmarking are explicitly watermarked everywhere in the UI so users never mistake test records for authentic legal statutes.',
      actionLabel: 'Browse Sources',
      linkHref: '/sources',
      preview: (
        <div className="space-y-3">
          <SafetyBanner
            variant="synthetic"
            title="Reference Corpus Watermark"
            message="REFERENCE CORPUS: The following data was generated for development, retrieval evaluation, and UI demonstration. It must not be presented as official legal advice."
          />
          <div className="bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-900 block">
                Reference Contract Sample 004
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                REF-DOC-004 • Hash: 7a9c8f...
              </span>
            </div>
            <SourceBadge authority="SYNTHETIC" synthetic={true} />
          </div>
        </div>
      ),
    },
    {
      id: 4,
      title: 'Side-by-Side Contract Comparison & Diffing',
      badge: 'Evaluation Touchpoint #4',
      category: 'Comparison',
      description:
        'Compares two contract drafts or amendments, highlighting shifted liabilities, changed notice durations, and emerging compliance risks.',
      actionLabel: 'Open Compare Tool',
      linkHref: '/compare',
      preview: (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="font-bold text-slate-700 block mb-1">Baseline (Version 1)</span>
              <p className="text-slate-600 font-mono text-[11px]">
                Notice Period: 30 days written notice.
              </p>
            </div>
            <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-xl">
              <span className="font-bold text-blue-800 block mb-1">Amended (Version 2)</span>
              <p className="text-slate-700 font-mono text-[11px]">
                Notice Period: 60 days + 2 months severance buyout.
              </p>
            </div>
          </div>
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800">
            <strong>Impact:</strong> Notice commitment doubled for both parties. Counterparty retains option to buy out remainder.
          </div>
        </div>
      ),
    },
    {
      id: 5,
      title: 'Lawyer Handoff Dossier Export',
      badge: 'Evaluation Touchpoint #5',
      category: 'Legal Integration',
      description:
        'Recognizing that LegalLens is an informational assistant, users can export an intake package with structured facts, statutory references, and targeted questions for qualified counsel.',
      actionLabel: 'Generate Handoff Dossier',
      preview: (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
            <UserCheck className="w-6 h-6" />
          </div>
          <h4 className="text-xs font-bold text-slate-900">
            Professional Intake Dossier Ready
          </h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Includes executive facts, identified statutory anchors, relevant precedents, and 3 targeted questions for your advocate.
          </p>
          <button
            onClick={() => setHandoffOpen(true)}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl shadow-xs transition"
          >
            Preview Lawyer Handoff Dossier
          </button>
        </div>
      ),
    },
  ];

  const current = TOUCHPOINTS.find((t) => t.id === activeStep) || TOUCHPOINTS[0];

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Title */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] text-blue-600 font-semibold uppercase tracking-wider">
            Evaluation & Showcase
          </span>
          <span className="text-xs text-slate-400">•</span>
          <span className="text-xs text-slate-500">End-to-End Touchpoints</span>
        </div>
        <h1 className="text-xl font-bold text-slate-900">
          LegalLens Guided Feature Walkthrough
        </h1>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl">
          Interactive showcase demonstrating evidence grounding, statutory citations, non-compete enforceability, provenance transparency, and lawyer intake dossiers.
        </p>
      </div>

      {/* Touchpoint Selector Tabs */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {TOUCHPOINTS.map((tp) => (
          <button
            key={tp.id}
            onClick={() => setActiveStep(tp.id)}
            className={`p-3 rounded-xl border text-left transition ${
              activeStep === tp.id
                ? 'border-blue-600 bg-blue-50/50 shadow-xs ring-1 ring-blue-500/20'
                : 'border-slate-200 bg-white hover:bg-slate-50'
            }`}
          >
            <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider block">
              Step {tp.id}
            </span>
            <span className="text-xs font-bold text-slate-800 line-clamp-1 block mt-0.5">
              {tp.category}
            </span>
          </button>
        ))}
      </div>

      {/* Main Touchpoint Viewer */}
      <div className="bg-slate-50/50 border border-slate-200 rounded-3xl p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200/80 pb-4">
          <div>
            <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider block">
              {current.badge}
            </span>
            <h2 className="text-base font-bold text-slate-900 mt-0.5">
              {current.title}
            </h2>
            <p className="text-xs text-slate-600 mt-1 max-w-2xl leading-relaxed">
              {current.description}
            </p>
          </div>

          {current.linkHref && (
            <Link
              href={current.linkHref}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 shadow-xs transition flex-shrink-0"
            >
              <span>{current.actionLabel}</span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </Link>
          )}
        </div>

        {/* Live Interactive Preview */}
        <div>{current.preview}</div>
      </div>

      {/* Modal */}
      <LawyerHandoffModal
        isOpen={handoffOpen}
        onClose={() => setHandoffOpen(false)}
        response={mockSampleAnswer}
      />
    </div>
  );
}
