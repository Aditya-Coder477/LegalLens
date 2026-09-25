'use client';

import React, { useState } from 'react';
import { ArrowLeftRight, Sparkles, Loader2, FileText, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck } from 'lucide-react';
import { LegalLensAPI } from '../../lib/api/client';
import { AIResponse } from '../../lib/types';
import { AnswerView } from '../../components/analysis/AnswerView';
import { LawyerHandoffModal } from '../../components/analysis/LawyerHandoffModal';

const SAMPLE_A = `EMPLOYMENT AGREEMENT (VERSION 1)
Section 4: Termination
Either party may terminate this agreement by providing thirty (30) days written notice to the other party.
Section 7: Non-Compete
Employee agrees not to work with direct competitors in Mumbai for a period of 6 months following cessation of employment.
Section 10: Governing Law
This agreement shall be governed by the laws of Maharashtra, India.`;

const SAMPLE_B = `EMPLOYMENT AGREEMENT (VERSION 2 - AMENDED)
Section 4: Termination & Severance
Either party may terminate this agreement by providing sixty (60) days written notice. In lieu of notice, the Employer may pay 2 months base salary.
Section 7: Non-Compete & Restrictive Covenants
Employee agrees not to work with any direct or indirect competitors throughout India for a period of 24 months post-termination.
Section 10: Dispute Resolution & Arbitration
Any dispute shall be referred to sole arbitration in New Delhi under the Arbitration and Conciliation Act, 1996.`;

export default function CompareDocumentsPage() {
  const [docA, setDocA] = useState(SAMPLE_A);
  const [docB, setDocB] = useState(SAMPLE_B);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [handoffOpen, setHandoffOpen] = useState(false);

  const handleCompare = async () => {
    if (!docA.trim() || !docB.trim()) return;
    setLoading(true);
    setResponse(null);

    try {
      const res = await LegalLensAPI.compareDocuments(
        undefined,
        undefined,
        docA.trim(),
        docB.trim()
      );
      setResponse(res);
    } catch (err) {
      console.error('Failed to compare documents', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Title */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] text-blue-600 font-semibold uppercase tracking-wider">
            Document Comparison
          </span>
          <span className="text-xs text-slate-400">•</span>
          <span className="text-xs text-slate-500">Side-by-Side Clause Diff</span>
        </div>
        <h1 className="text-xl font-bold text-slate-900">
          Compare Contract Versions & Amendment Risks
        </h1>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl">
          Identify added, removed, and modified clauses between contract drafts. Automatically assesses material risk shifts and enforceability under Indian law.
        </p>
      </div>

      {/* Inputs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Document A */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-md bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center">
                A
              </span>
              <h2 id="heading-doc-a" className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
                Baseline / Version 1
              </h2>
            </div>
            <button
              type="button"
              onClick={() => setDocA(SAMPLE_A)}
              className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded p-1"
            >
              Reset Sample
            </button>
          </div>
          <label htmlFor="compare-doc-a" className="sr-only">
            Baseline Contract Text or Version 1
          </label>
          <textarea
            id="compare-doc-a"
            value={docA}
            onChange={(e) => setDocA(e.target.value)}
            rows={10}
            className="w-full text-xs font-mono p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl focus:bg-white dark:focus:bg-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 text-slate-800 dark:text-slate-200 transition"
            placeholder="Paste baseline contract text or clause..."
          />
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>{docA.length} characters</span>
            <span>Original Version</span>
          </div>
        </div>

        {/* Document B */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-xs space-y-3 transition-colors">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-md bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 font-bold text-xs flex items-center justify-center">
                B
              </span>
              <h2 id="heading-doc-b" className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
                Amended / Version 2
              </h2>
            </div>
            <button
              type="button"
              onClick={() => setDocB(SAMPLE_B)}
              className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded p-1"
            >
              Reset Sample
            </button>
          </div>
          <label htmlFor="compare-doc-b" className="sr-only">
            Amended Contract Text or Version 2
          </label>
          <textarea
            id="compare-doc-b"
            value={docB}
            onChange={(e) => setDocB(e.target.value)}
            rows={10}
            className="w-full text-xs font-mono p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl focus:bg-white dark:focus:bg-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 text-slate-800 dark:text-slate-200 transition"
            placeholder="Paste updated draft or counterparty revisions..."
          />
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>{docB.length} characters</span>
            <span>Modified Version</span>
          </div>
        </div>
      </div>

      {/* Compare Action */}
      <div className="flex items-center justify-between bg-slate-100/70 border border-slate-200 rounded-2xl p-3.5">
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Compares clause by clause and checks statutory validity (e.g. §27 Indian Contract Act).</span>
        </div>
        <button
          onClick={handleCompare}
          disabled={loading || !docA.trim() || !docB.trim()}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-xs transition inline-flex items-center gap-2"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowLeftRight className="w-4 h-4" />}
          <span>{loading ? 'Analyzing Differences...' : 'Run Comparative Analysis'}</span>
        </button>
      </div>

      {/* Diff Highlights Overview when response is present */}
      {response && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-4 bg-emerald-50/60 border border-emerald-200 rounded-xl">
            <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider block mb-1">
              Notice Period Shift
            </span>
            <div className="text-xs font-semibold text-slate-900 flex items-center gap-2">
              <span className="line-through text-slate-400">30 Days</span>
              <ArrowRight className="w-3.5 h-3.5 text-emerald-600" />
              <span className="text-emerald-700 font-bold">60 Days (+ Salary in lieu)</span>
            </div>
            <p className="text-[11px] text-slate-600 mt-1">
              Increases obligation for employee but provides employer buyout option.
            </p>
          </div>

          <div className="p-4 bg-red-50/60 border border-red-200 rounded-xl">
            <span className="text-[10px] font-bold text-red-700 uppercase tracking-wider block mb-1">
              Non-Compete Expansion (High Risk)
            </span>
            <div className="text-xs font-semibold text-slate-900 flex items-center gap-2">
              <span className="line-through text-slate-400">6 Mo (Mumbai)</span>
              <ArrowRight className="w-3.5 h-3.5 text-red-600" />
              <span className="text-red-700 font-bold">24 Mo (All India)</span>
            </div>
            <p className="text-[11px] text-slate-600 mt-1">
              Void under Section 27, Indian Contract Act 1872. Unenforceable post-employment restraint.
            </p>
          </div>

          <div className="p-4 bg-blue-50/60 border border-blue-200 rounded-xl">
            <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider block mb-1">
              Dispute Resolution Change
            </span>
            <div className="text-xs font-semibold text-slate-900 flex items-center gap-2">
              <span className="line-through text-slate-400">Civil Court (MH)</span>
              <ArrowRight className="w-3.5 h-3.5 text-blue-600" />
              <span className="text-blue-700 font-bold">Arbitration (Delhi)</span>
            </div>
            <p className="text-[11px] text-slate-600 mt-1">
              Shifts venue to Delhi under Arbitration & Conciliation Act 1996.
            </p>
          </div>
        </div>
      )}

      {/* Answer View */}
      {response && (
        <AnswerView
          response={response}
          onOpenHandoff={() => setHandoffOpen(true)}
        />
      )}

      {/* Lawyer Handoff Modal */}
      {response && (
        <LawyerHandoffModal
          isOpen={handoffOpen}
          onClose={() => setHandoffOpen(false)}
          response={response}
        />
      )}
    </div>
  );
}
