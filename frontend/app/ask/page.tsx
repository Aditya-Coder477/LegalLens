'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { Search, Loader2, Sparkles, AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react';
import { LegalLensAPI } from '../../lib/api/client';
import { AIResponse } from '../../lib/types';
import { AnswerView } from '../../components/analysis/AnswerView';

const LawyerHandoffModal = dynamic(
  () => import('../../components/analysis/LawyerHandoffModal').then((mod) => mod.LawyerHandoffModal),
  { ssr: false }
);

function AskPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialQuery = searchParams.get('q') || '';

  const [query, setQuery] = useState(initialQuery);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [handoffOpen, setHandoffOpen] = useState(false);

  const handleAsk = async (queryText: string) => {
    if (!queryText.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    setResponse(null);
    setStatusMessage('Searching statutory provisions and indexed agreements...');

    try {
      setTimeout(() => {
        setStatusMessage('Extracting relevant clauses and checking citations...');
      }, 700);

      const res = await LegalLensAPI.askLegalLens(queryText.trim());
      setResponse(res);
      setStatusMessage('');
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'Unable to retrieve legal evidence for this inquiry. No changes were made.');
      setStatusMessage('');
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
      {/* Page Title & Scope */}
      <header className="space-y-1">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100">
          Ask about your legal information
        </h1>
        <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">
          Ask questions about your selected documents and inspect the evidence supporting the response. Every claim is grounded in verifiable legal sources.
        </p>
      </header>

      {/* Query Bar */}
      <form
        role="search"
        aria-label="Ask about legal documents"
        onSubmit={handleSubmit}
        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-2 shadow-sm flex items-center gap-2 transition-colors focus-within:ring-2 focus-within:ring-blue-600"
      >
        <label htmlFor="ask-query-input" className="sr-only">
          Enter your legal question
        </label>
        <Search className="w-5 h-5 text-slate-400 ml-3 shrink-0 pointer-events-none" aria-hidden="true" />
        <input
          id="ask-query-input"
          type="text"
          placeholder="Ask a question (e.g. What notice period is required for termination without cause?)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="flex-1 bg-transparent py-2.5 px-2 text-xs font-medium text-slate-900 dark:text-slate-100 placeholder-slate-400 focus-visible:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          aria-label={loading ? 'Analyzing legal question...' : 'Submit question to AI assistant'}
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-xs transition shrink-0 inline-flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          ) : (
            <Sparkles className="w-4 h-4" aria-hidden="true" />
          )}
          <span>{loading ? 'Analyzing...' : 'Ask Assistant'}</span>
        </button>
      </form>

      {/* Live progress announcement for assistive technology */}
      <div aria-live="polite" aria-atomic="true">
        {loading && (
          <div className="bg-blue-50/50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/60 rounded-xl p-8 text-center space-y-3">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600 dark:text-blue-400 mx-auto" aria-hidden="true" />
            <h2 className="text-xs font-bold text-slate-800 dark:text-slate-200">
              Retrieving Legal Evidence
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-sm mx-auto">
              {statusMessage || 'Searching statutory provisions and checking citations...'}
            </p>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div
          role="alert"
          className="p-4 rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 text-xs text-rose-800 dark:text-rose-300 flex items-center justify-between gap-4"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <p className="font-semibold">{errorMsg}</p>
              <p className="text-rose-600 dark:text-rose-400 mt-0.5">Please check your query or try rephrasing.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => handleAsk(query)}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
          >
            <RefreshCw className="w-3 h-3" aria-hidden="true" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Suggested Questions */}
      {!response && !loading && (
        <section aria-labelledby="suggested-queries-heading" className="bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl p-6">
          <h2 id="suggested-queries-heading" className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-3 uppercase tracking-wider">
            Suggested Inquiries
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              'What happens if I terminate employment early without cause?',
              'What are the data erasure duties of an intermediary under the Act?',
              'What exceptions apply to mandatory termination notice?',
              'What are the obligations regarding return of company property on termination?',
            ].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => {
                  setQuery(s);
                  handleAsk(s);
                }}
                className="text-left text-xs bg-white dark:bg-slate-800 hover:bg-blue-50/60 dark:hover:bg-slate-700 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-300 text-slate-700 dark:text-slate-300 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
              >
                {s}
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Answer View */}
      {response && !loading && (
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

export default function AskPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center" aria-live="polite">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" aria-hidden="true" />
          <span className="text-xs text-slate-500">Loading inquiry workspace...</span>
        </div>
      }
    >
      <AskPageContent />
    </Suspense>
  );
}
