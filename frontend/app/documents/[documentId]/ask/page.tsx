'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Search, Sparkles, Loader2 } from 'lucide-react';
import { LegalLensAPI } from '../../../../lib/api/client';
import { AIResponse } from '../../../../lib/types';
import { AnswerView } from '../../../../components/analysis/AnswerView';
import { LawyerHandoffModal } from '../../../../components/analysis/LawyerHandoffModal';

export default function DocumentScopedAskPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params?.documentId as string;

  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [handoffOpen, setHandoffOpen] = useState(false);

  const handleAsk = async (queryText: string) => {
    if (!queryText.trim()) return;
    setLoading(true);
    setResponse(null);

    try {
      const res = await LegalLensAPI.askLegalLens(queryText.trim(), documentId);
      setResponse(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      handleAsk(query);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Back button and title */}
      <div className="flex items-center gap-3">
        <Link
          href={`/documents/${documentId}`}
          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <span className="text-[11px] text-blue-600 font-semibold uppercase tracking-wider block">
            Document-Scoped Q&A
          </span>
          <h1 className="text-base font-bold text-slate-900">
            Ask about <span className="font-mono text-xs">{documentId}</span>
          </h1>
        </div>
      </div>

      {/* Query Bar */}
      <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-2xl p-2 shadow-sm flex items-center gap-2">
        <Search className="w-5 h-5 text-slate-400 ml-3 flex-shrink-0" />
        <input
          type="text"
          placeholder={`Ask a question specifically regarding ${documentId}...`}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="flex-1 bg-transparent py-2.5 px-2 text-xs font-medium focus:outline-hidden text-slate-900"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-xs transition flex-shrink-0 inline-flex items-center gap-1.5"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          <span>{loading ? 'Analyzing...' : 'Ask Document'}</span>
        </button>
      </form>

      {/* Quick Prompts */}
      {!response && !loading && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-5">
          <span className="text-xs font-bold text-slate-700 block mb-2.5 uppercase tracking-wider">
            Suggested Questions for this Document
          </span>
          <div className="flex flex-wrap gap-2">
            {[
              'What are my termination notice obligations?',
              'What happens to company property on exit?',
              'Are there exceptions for summary dismissal?',
              'What governing law applies to disputes?',
            ].map((s) => (
              <button
                key={s}
                onClick={() => {
                  setQuery(s);
                  handleAsk(s);
                }}
                className="text-xs bg-white hover:bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 transition"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="py-20 flex flex-col items-center justify-center text-slate-500 gap-3">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          <div className="text-xs font-medium text-slate-700">
            Querying document evidence and verifying citations...
          </div>
        </div>
      )}

      {/* Answer View */}
      {response && (
        <AnswerView
          response={response}
          onNavigateToDocument={(docId, sec, page) => {
            router.push(`/documents/${docId}${sec ? `?sec=${encodeURIComponent(sec)}` : ''}`);
          }}
          onOpenLawyerHandoff={() => setHandoffOpen(true)}
        />
      )}

      {/* Lawyer Handoff Modal */}
      <LawyerHandoffModal
        isOpen={handoffOpen}
        onClose={() => setHandoffOpen(false)}
        response={response}
      />
    </div>
  );
}
