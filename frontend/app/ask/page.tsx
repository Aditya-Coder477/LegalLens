'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Search, Loader2, Sparkles, AlertCircle, ArrowLeft } from 'lucide-react';
import { LegalLensAPI } from '../../lib/api/client';
import { AIResponse } from '../../lib/types';
import { AnswerView } from '../../components/analysis/AnswerView';
import { LawyerHandoffModal } from '../../components/analysis/LawyerHandoffModal';

function AskPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialQuery = searchParams.get('q') || '';

  const [query, setQuery] = useState(initialQuery);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [handoffOpen, setHandoffOpen] = useState(false);

  const handleAsk = async (queryText: string) => {
    if (!queryText.trim()) return;
    setLoading(true);
    setResponse(null);

    try {
      const res = await LegalLensAPI.askLegalLens(queryText.trim());
      setResponse(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialQuery) {
      handleAsk(initialQuery);
    }
  }, [initialQuery]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      handleAsk(query);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 mb-1">Ask LegalLens AI</h1>
        <p className="text-xs text-slate-500">
          Query statutory provisions, contractual obligations, and legal precedents with strict evidence grounding and citation verification.
        </p>
      </div>

      {/* Query Bar */}
      <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-2xl p-2 shadow-sm flex items-center gap-2">
        <Search className="w-5 h-5 text-slate-400 ml-3 flex-shrink-0" />
        <input
          type="text"
          placeholder="Ask any legal question (e.g. What are the mandatory grounds for summary dismissal?)"
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
          <span>{loading ? 'Analyzing...' : 'Ask Assistant'}</span>
        </button>
      </form>

      {/* Suggested Questions */}
      {!response && !loading && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-6">
          <span className="text-xs font-bold text-slate-700 block mb-3 uppercase tracking-wider">
            Suggested Legal Queries
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              'What happens if I terminate employment early without cause?',
              'What are the data erasure duties of an intermediary under the Act?',
              'What exceptions apply to mandatory termination notice?',
              'What are the obligations regarding return of company property on termination?',
            ].map((s) => (
              <button
                key={s}
                onClick={() => {
                  setQuery(s);
                  handleAsk(s);
                }}
                className="text-left text-xs bg-white hover:bg-blue-50/60 p-3 rounded-lg border border-slate-200 hover:border-blue-200 text-slate-700 transition"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading Indicator */}
      {loading && (
        <div className="py-20 flex flex-col items-center justify-center text-slate-500 gap-3">
          <Loader2 className="w-9 h-9 text-blue-600 animate-spin" />
          <div className="text-xs font-medium text-slate-700">
            Retrieving legal evidence and validating claims...
          </div>
          <span className="text-[11px] text-slate-400">
            Hybrid RAG • Entailment Scoring • SHA-256 Provenance Audit
          </span>
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

export default function AskPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center text-xs text-slate-500">
          Loading LegalLens workspace...
        </div>
      }
    >
      <AskPageContent />
    </Suspense>
  );
}
