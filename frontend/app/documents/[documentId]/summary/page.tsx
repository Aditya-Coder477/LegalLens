'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, FileText, Sparkles, Loader2, RefreshCw } from 'lucide-react';
import { LegalLensAPI } from '../../../../lib/api/client';
import dynamic from 'next/dynamic';
import { AIResponse, DocumentDetail } from '../../../../lib/types';
import { AnswerView } from '../../../../components/analysis/AnswerView';

const LawyerHandoffModal = dynamic(
  () => import('../../../../components/analysis/LawyerHandoffModal').then((mod) => mod.LawyerHandoffModal),
  { ssr: false }
);

export default function DocumentSummaryPage() {
  const params = useParams();
  const documentId = params?.documentId as string;

  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [handoffOpen, setHandoffOpen] = useState(false);

  useEffect(() => {
    async function loadData() {
      if (!documentId) return;
      try {
        const docData = await LegalLensAPI.getDocument(documentId);
        setDoc(docData);
      } catch (err) {
        console.error('Failed to load document info', err);
      }
    }
    loadData();
  }, [documentId]);

  const generateSummary = async () => {
    setLoading(true);
    try {
      const res = await LegalLensAPI.summarizeDocument(documentId);
      setResponse(res);
    } catch (err) {
      console.error('Failed to summarize document', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    generateSummary();
  }, [documentId]);

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex items-center justify-between">
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
                Document Summary
              </span>
              <span className="text-xs text-slate-400">•</span>
              <span className="text-xs font-mono text-slate-500">{documentId}</span>
            </div>
            <h1 className="text-base font-bold text-slate-900">
              {doc?.title || 'Executive Summary'}
            </h1>
          </div>
        </div>

        <button
          onClick={generateSummary}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition"
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          <span>Regenerate Summary</span>
        </button>
      </div>

      {/* Loading state */}
      {loading && !response && (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center shadow-xs">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" />
          <h3 className="text-xs font-bold text-slate-800">Synthesizing Document Summary</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
            Analyzing text segments, retrieving statutory anchors, and compiling structured key points...
          </p>
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
