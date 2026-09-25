'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, Sparkles, Loader2, ShieldAlert, CheckCircle2, AlertTriangle, BookOpen } from 'lucide-react';
import { LegalLensAPI } from '../../../../lib/api/client';
import { AIResponse } from '../../../../lib/types';
import { AnswerView } from '../../../../components/analysis/AnswerView';
import { LawyerHandoffModal } from '../../../../components/analysis/LawyerHandoffModal';

const PRESET_CLAUSES = [
  {
    title: 'Termination & Notice Clause',
    category: 'Termination',
    text: 'Either party may terminate this Agreement by giving thirty (30) days written notice to the other party, or salary in lieu thereof. The Company reserves the right to terminate employment immediately without notice in the event of gross misconduct.',
  },
  {
    title: 'Post-Employment Non-Compete Clause',
    category: 'Restrictive Covenants',
    text: 'For a period of 12 months following termination of employment for any reason, Employee shall not directly or indirectly engage in, perform services for, or establish any business competing with the Company within the territory of India.',
  },
  {
    title: 'Confidentiality & Non-Disclosure',
    category: 'Confidentiality',
    text: 'The Employee acknowledges that during employment they will have access to confidential proprietary information. The Employee agrees to maintain strict confidentiality during and indefinitely after the cessation of employment.',
  },
  {
    title: 'Limitation of Liability & Indemnity',
    category: 'Liability',
    text: 'The Employee agrees to indemnify and hold harmless the Company against any damages, losses, or legal costs arising from any breach of covenants or negligent performance of duties.',
  },
];

export default function DocumentClausesPage() {
  const params = useParams();
  const documentId = params?.documentId as string;

  const [selectedText, setSelectedText] = useState(PRESET_CLAUSES[0].text);
  const [customText, setCustomText] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [handoffOpen, setHandoffOpen] = useState(false);

  const handleAnalyze = async (clauseToAnalyze: string) => {
    if (!clauseToAnalyze.trim()) return;
    setLoading(true);
    setResponse(null);

    try {
      const res = await LegalLensAPI.analyzeClause(clauseToAnalyze, documentId);
      setResponse(res);
    } catch (err) {
      console.error('Failed to analyze clause', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href={`/documents/${documentId}`}
          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-blue-600 font-semibold uppercase tracking-wider">
              Clause Intelligence & Risk Analysis
            </span>
            <span className="text-xs text-slate-400">•</span>
            <span className="text-xs font-mono text-slate-500">{documentId}</span>
          </div>
          <h1 className="text-base font-bold text-slate-900">
            Legal Clause Review & Enforceability Assessment
          </h1>
        </div>
      </div>

      {/* Preset Clause Selector */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <BookOpen className="w-4 h-4 text-blue-600" />
            <span>Select or Paste Clause for Analysis</span>
          </h2>
          <span className="text-[11px] text-slate-500">Evaluated against statutory provisions</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {PRESET_CLAUSES.map((clause, idx) => (
            <button
              key={idx}
              onClick={() => {
                setSelectedText(clause.text);
                setCustomText('');
              }}
              className={`p-3 text-left rounded-xl border transition ${
                selectedText === clause.text && !customText
                  ? 'border-blue-500 bg-blue-50/50 shadow-xs ring-1 ring-blue-500/20'
                  : 'border-slate-200 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-slate-800">{clause.title}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold">
                  {clause.category}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                {clause.text}
              </p>
            </button>
          ))}
        </div>

        {/* Text Area */}
        <div className="space-y-2 pt-2">
          <label className="text-xs font-medium text-slate-700 block">
            Clause Text Under Review:
          </label>
          <textarea
            value={customText || selectedText}
            onChange={(e) => {
              setCustomText(e.target.value);
              setSelectedText('');
            }}
            rows={4}
            placeholder="Paste any custom clause text here to analyze its enforceability and risks..."
            className="w-full text-xs font-mono p-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800 transition"
          />
        </div>

        <div className="flex items-center justify-between pt-1">
          <span className="text-[11px] text-slate-500">
            Assesses Indian statutory compliance (e.g. Contract Act §27, Industrial Disputes Act).
          </span>
          <button
            onClick={() => handleAnalyze(customText || selectedText)}
            disabled={loading || !(customText || selectedText).trim()}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-xs transition inline-flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            <span>{loading ? 'Analyzing Clause...' : 'Analyze Clause Enforceability'}</span>
          </button>
        </div>
      </div>

      {/* Analysis Result */}
      {response && (
        <div className="space-y-4">
          <AnswerView
            response={response}
            onOpenHandoff={() => setHandoffOpen(true)}
          />
        </div>
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
