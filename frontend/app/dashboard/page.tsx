'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  FileText,
  Search,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Clock,
  Layers,
  Activity,
  PlusCircle,
  UploadCloud,
  CheckCircle2,
  FileCheck,
  Scale,
  Shield,
  HelpCircle,
} from 'lucide-react';
import { LegalLensAPI } from '../../lib/api/client';
import { DashboardStats, DocumentSummary } from '../../lib/types';
import { DocumentCard } from '../../components/documents/DocumentCard';
import { UploadDropzone } from '../../components/documents/UploadDropzone';
import { formatDate } from '../../lib/utils/cn';

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploadedDoc, setUploadedDoc] = useState<DocumentSummary | null>(null);
  const router = useRouter();

  useEffect(() => {
    LegalLensAPI.getDashboard()
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load dashboard stats:', err);
        setLoading(false);
      });
  }, []);

  const handleAskSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/ask?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const handleUploadSuccess = (newDoc: DocumentSummary) => {
    setUploadedDoc(newDoc);
    setStats((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        total_documents: prev.total_documents + 1,
        recent_documents: [newDoc, ...prev.recent_documents.filter((d) => d.document_id !== newDoc.document_id)],
      };
    });
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Hero Ask Box */}
      <div className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white rounded-2xl p-8 shadow-sm">
        <div className="max-w-2xl">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-blue-100 backdrop-blur-xs mb-3">
            <Sparkles className="w-3.5 h-3.5 text-blue-300" />
            <span>Evidence-Grounded Legal Intelligence</span>
          </span>
          <h1 className="text-2xl font-bold tracking-tight mb-2">
            What legal question do you want to understand today?
          </h1>
          <p className="text-xs text-blue-100 mb-6 leading-relaxed">
            Search across statutory enactments, commercial agreements, and judicial precedents with claim-level provenance and SHA-256 verification.
          </p>

          <form onSubmit={handleAskSubmit} className="relative flex items-center">
            <Search className="w-5 h-5 text-slate-400 absolute left-4" />
            <input
              type="text"
              placeholder="e.g. What happens if I terminate employment early without cause?"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white text-slate-900 pl-11 pr-28 py-3.5 rounded-xl text-xs font-medium shadow-md focus:outline-hidden focus:ring-2 focus:ring-blue-400"
            />
            <button
              type="submit"
              className="absolute right-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition"
            >
              Ask AI
            </button>
          </form>

          {/* Suggested Prompts */}
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
            <span className="text-blue-200 text-[11px]">Suggested:</span>
            {[
              'Termination notice requirements',
              'Data fiduciary deletion obligations',
              'Non-compete clause validity',
            ].map((s) => (
              <button
                key={s}
                onClick={() => router.push(`/ask?q=${encodeURIComponent(s)}`)}
                className="bg-white/10 hover:bg-white/20 text-white px-2.5 py-1 rounded-md text-[11px] transition"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Upload Document Section directly on Dashboard */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs">
                <UploadCloud className="w-3.5 h-3.5" />
              </span>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Upload Document & Run Instant AI Analysis
              </h2>
            </div>
          </div>

          {uploadedDoc && (
            <button
              onClick={() => setUploadedDoc(null)}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition"
            >
              + Upload Another File
            </button>
          )}
        </div>

        {/* If a document was just uploaded, show success & instant analysis triggers */}
        {uploadedDoc ? (
          <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-5 space-y-4 animate-in fade-in duration-200">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider block">
                    Document Successfully Indexed
                  </span>
                  <h3 className="text-sm font-bold text-slate-900">{uploadedDoc.title}</h3>
                  <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono mt-0.5">
                    <span>ID: {uploadedDoc.document_id}</span>
                    <span>•</span>
                    <span>{uploadedDoc.chunk_count} chunks indexed</span>
                    <span>•</span>
                    <span>{uploadedDoc.page_count} pages</span>
                  </div>
                </div>
              </div>

              <Link
                href={`/documents/${uploadedDoc.document_id}`}
                className="px-4 py-2 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg text-xs font-semibold text-slate-800 shadow-xs transition"
              >
                Open Viewer
              </Link>
            </div>

            {/* Instant AI Action Buttons */}
            <div className="pt-2 border-t border-emerald-200/60">
              <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block mb-2">
                Run Instant AI Intelligence on This Document:
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <Link
                  href={`/documents/${uploadedDoc.document_id}/clauses`}
                  className="p-3 bg-white hover:bg-blue-50/50 border border-slate-200 hover:border-blue-300 rounded-xl transition flex flex-col items-start gap-1 group"
                >
                  <Scale className="w-4 h-4 text-blue-600 group-hover:scale-110 transition-transform" />
                  <span className="text-xs font-bold text-slate-800">Clause Analysis</span>
                  <span className="text-[10px] text-slate-500">Assess S.27 enforceability</span>
                </Link>

                <Link
                  href={`/documents/${uploadedDoc.document_id}/summary`}
                  className="p-3 bg-white hover:bg-blue-50/50 border border-slate-200 hover:border-blue-300 rounded-xl transition flex flex-col items-start gap-1 group"
                >
                  <FileCheck className="w-4 h-4 text-indigo-600 group-hover:scale-110 transition-transform" />
                  <span className="text-xs font-bold text-slate-800">Executive Summary</span>
                  <span className="text-[10px] text-slate-500">Extract structured key points</span>
                </Link>

                <Link
                  href={`/documents/${uploadedDoc.document_id}/obligations`}
                  className="p-3 bg-white hover:bg-blue-50/50 border border-slate-200 hover:border-blue-300 rounded-xl transition flex flex-col items-start gap-1 group"
                >
                  <Shield className="w-4 h-4 text-emerald-600 group-hover:scale-110 transition-transform" />
                  <span className="text-xs font-bold text-slate-800">Party Obligations</span>
                  <span className="text-[10px] text-slate-500">Covenants & conditions</span>
                </Link>

                <Link
                  href={`/documents/${uploadedDoc.document_id}/ask`}
                  className="p-3 bg-white hover:bg-blue-50/50 border border-slate-200 hover:border-blue-300 rounded-xl transition flex flex-col items-start gap-1 group"
                >
                  <Sparkles className="w-4 h-4 text-purple-600 group-hover:scale-110 transition-transform" />
                  <span className="text-xs font-bold text-slate-800">Ask Document</span>
                  <span className="text-[10px] text-slate-500">Strictly grounded Q&A</span>
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <UploadDropzone onUploadSuccess={handleUploadSuccess} />
        )}
      </div>

      {/* Stats Counter Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center font-bold">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-medium text-slate-500 block">Indexed Documents</span>
            <span className="text-2xl font-bold text-slate-900">
              {loading ? '...' : stats?.total_documents || 168}
            </span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-700 flex items-center justify-center font-bold">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-medium text-slate-500 block">Completed Analyses</span>
            <span className="text-2xl font-bold text-slate-900">
              {loading ? '...' : stats?.total_analyses || 32}
            </span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center font-bold">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-medium text-slate-500 block">Pending Reviews</span>
            <span className="text-2xl font-bold text-slate-900">
              {loading ? '...' : stats?.pending_actions || 3}
            </span>
          </div>
        </div>
      </div>

      {/* Recent Documents & Activity Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Recent Documents */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Recent Documents
            </h2>
            <Link
              href="/documents"
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center gap-1 transition"
            >
              <span>View all ({stats?.total_documents || 168})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {(stats?.recent_documents || []).map((doc) => (
              <DocumentCard key={doc.document_id} document={doc} />
            ))}
          </div>
        </div>

        {/* Right 1 Col: Recent Activity */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Recent Activity
            </h2>
            <span className="text-xs font-semibold text-slate-400">
              Forensic Log
            </span>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 divide-y divide-slate-100 shadow-xs">
            {(stats?.recent_activity || []).map((act) => (
              <div key={act.event_id} className="py-3 first:pt-0 last:pb-0">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-semibold text-slate-800">{act.title}</span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {formatDate(act.timestamp)}
                  </span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed mb-1.5">
                  {act.description}
                </p>
                {act.badge && (
                  <span className="inline-block px-1.5 py-0.2 rounded text-[10px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                    {act.badge}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
