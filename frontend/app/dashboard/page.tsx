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
  GitCompare,
  MessageSquareText,
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

  const quickActions = [
    {
      title: 'Upload Document',
      desc: 'Add PDF or text contract',
      icon: UploadCloud,
      href: '#upload-zone',
      action: () => {
        document.getElementById('doc-upload-input')?.click();
      },
    },
    {
      title: 'Ask a Question',
      desc: 'Evidence-backed inquiry',
      icon: MessageSquareText,
      href: '/ask',
    },
    {
      title: 'Summarize Document',
      desc: 'Executive breakdown',
      icon: FileCheck,
      href: '/documents/SYN-CONT-001/summary',
    },
    {
      title: 'Analyze Clauses',
      desc: 'Risk & enforceability',
      icon: Scale,
      href: '/documents/SYN-CONT-001/clauses',
    },
    {
      title: 'Find Obligations',
      desc: 'Party responsibilities',
      icon: Shield,
      href: '/documents/SYN-CONT-001/obligations',
    },
    {
      title: 'Find Deadlines',
      desc: 'Notice & cure dates',
      icon: Clock,
      href: '/documents/SYN-CONT-001/deadlines',
    },
    {
      title: 'Compare Versions',
      desc: 'Side-by-side diff',
      icon: GitCompare,
      href: '/compare',
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* 1. Page Header & Hero Inquiry Box */}
      <section
        aria-labelledby="dashboard-heading"
        className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white rounded-2xl p-6 sm:p-8 shadow-sm"
      >
        <div className="max-w-2xl space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-blue-100 backdrop-blur-xs">
            <Sparkles className="w-3.5 h-3.5 text-blue-300" aria-hidden="true" />
            <span>Evidence-Grounded Legal Intelligence</span>
          </div>

          <h1 id="dashboard-heading" className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            What legal question do you want to understand today?
          </h1>

          <p className="text-xs sm:text-sm text-blue-100 leading-relaxed font-normal">
            Review a document, find relevant evidence, or understand your obligations and deadlines across statutory enactments and commercial agreements.
          </p>

          <form
            role="search"
            aria-label="Search legal provisions on dashboard"
            onSubmit={handleAskSubmit}
            className="relative flex items-center pt-2"
          >
            <label htmlFor="dashboard-query-input" className="sr-only">
              Enter your legal question or contract inquiry
            </label>
            <Search className="w-5 h-5 text-slate-400 absolute left-4 pointer-events-none" aria-hidden="true" />
            <input
              id="dashboard-query-input"
              type="text"
              placeholder="e.g. What notice period is required for contract termination?"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white text-slate-900 pl-11 pr-28 py-3.5 rounded-xl text-xs font-medium shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
            />
            <button
              type="submit"
              aria-label="Submit legal question to AI"
              className="absolute right-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              Ask AI
            </button>
          </form>

          {/* Suggested Prompts */}
          <div className="pt-2 flex flex-wrap items-center gap-2 text-xs">
            <span className="text-blue-200 text-xs font-medium">Suggested queries:</span>
            {[
              'Termination notice requirements',
              'Data fiduciary deletion obligations',
              'Non-compete clause validity',
            ].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => router.push(`/ask?q=${encodeURIComponent(s)}`)}
                className="bg-white/10 hover:bg-white/20 text-white px-2.5 py-1 rounded-md text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 2. Primary Quick Actions Section */}
      <section aria-labelledby="quick-actions-heading" className="space-y-3">
        <h2 id="quick-actions-heading" className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          Primary Actions
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {quickActions.map((action) => {
            const Icon = action.icon;
            const content = (
              <div className="p-3 bg-white dark:bg-slate-900 hover:bg-blue-50/50 dark:hover:bg-blue-950/40 border border-slate-200 dark:border-slate-800 hover:border-blue-300 dark:hover:border-blue-700 rounded-xl transition text-left h-full flex flex-col justify-between group shadow-xs">
                <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-2 group-hover:scale-105 transition-transform">
                  <Icon className="w-4 h-4" aria-hidden="true" />
                </div>
                <div>
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block group-hover:text-blue-600 dark:group-hover:text-blue-400 transition">
                    {action.title}
                  </span>
                  <span className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight block mt-0.5">
                    {action.desc}
                  </span>
                </div>
              </div>
            );

            if (action.action) {
              return (
                <button
                  key={action.title}
                  type="button"
                  onClick={action.action}
                  aria-label={action.title}
                  className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded-xl text-left"
                >
                  {content}
                </button>
              );
            }

            return (
              <Link
                key={action.title}
                href={action.href}
                className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded-xl block"
              >
                {content}
              </Link>
            );
          })}
        </div>
      </section>

      {/* 3. Upload Document Section */}
      <section
        id="upload-zone"
        aria-labelledby="upload-heading"
        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs space-y-4 transition-colors"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-lg bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 flex items-center justify-center font-bold text-xs">
              <UploadCloud className="w-3.5 h-3.5" aria-hidden="true" />
            </span>
            <h2 id="upload-heading" className="text-sm font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
              Upload Document & Run Instant AI Analysis
            </h2>
          </div>

          {uploadedDoc && (
            <button
              type="button"
              onClick={() => setUploadedDoc(null)}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded p-1"
            >
              + Upload Another File
            </button>
          )}
        </div>

        {/* If a document was just uploaded, show success & instant analysis triggers */}
        {uploadedDoc ? (
          <div className="bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-xl p-5 space-y-4 animate-in fade-in duration-200">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-5 h-5" aria-hidden="true" />
                </div>
                <div>
                  <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider block">
                    Document Successfully Indexed
                  </span>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{uploadedDoc.title}</h3>
                  <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 font-mono mt-0.5">
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
                className="px-4 py-2 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 shadow-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
              >
                Open Viewer
              </Link>
            </div>

            {/* Instant AI Action Buttons */}
            <div className="pt-2 border-t border-emerald-200/60 dark:border-emerald-800/60">
              <span className="text-xs font-bold text-emerald-800 dark:text-emerald-300 block mb-2">
                1-Click Instant Analysis Options:
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Link
                  href={`/documents/${uploadedDoc.document_id}/summary`}
                  className="p-3 bg-white dark:bg-slate-800 hover:bg-blue-50/50 dark:hover:bg-blue-950/40 border border-slate-200 dark:border-slate-700 hover:border-blue-300 rounded-xl transition flex flex-col items-start gap-1 group shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                >
                  <FileCheck className="w-4 h-4 text-blue-600 group-hover:scale-110 transition-transform" aria-hidden="true" />
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Summarize</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">Plain-language review</span>
                </Link>

                <Link
                  href={`/documents/${uploadedDoc.document_id}/clauses`}
                  className="p-3 bg-white dark:bg-slate-800 hover:bg-blue-50/50 dark:hover:bg-blue-950/40 border border-slate-200 dark:border-slate-700 hover:border-blue-300 rounded-xl transition flex flex-col items-start gap-1 group shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                >
                  <Scale className="w-4 h-4 text-purple-600 group-hover:scale-110 transition-transform" aria-hidden="true" />
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Analyze Clauses</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">Risks & indemnity</span>
                </Link>

                <Link
                  href={`/documents/${uploadedDoc.document_id}/obligations`}
                  className="p-3 bg-white dark:bg-slate-800 hover:bg-blue-50/50 dark:hover:bg-blue-950/40 border border-slate-200 dark:border-slate-700 hover:border-blue-300 rounded-xl transition flex flex-col items-start gap-1 group shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                >
                  <Shield className="w-4 h-4 text-emerald-600 group-hover:scale-110 transition-transform" aria-hidden="true" />
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Party Obligations</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">Covenants & conditions</span>
                </Link>

                <Link
                  href={`/documents/${uploadedDoc.document_id}/ask`}
                  className="p-3 bg-white dark:bg-slate-800 hover:bg-blue-50/50 dark:hover:bg-blue-950/40 border border-slate-200 dark:border-slate-700 hover:border-blue-300 rounded-xl transition flex flex-col items-start gap-1 group shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                >
                  <Sparkles className="w-4 h-4 text-purple-600 group-hover:scale-110 transition-transform" aria-hidden="true" />
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Ask Document</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">Strictly grounded Q&A</span>
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <UploadDropzone onUploadSuccess={handleUploadSuccess} />
        )}
      </section>

      {/* 4. Stats Counter Grid */}
      <section aria-labelledby="stats-heading" className="space-y-3">
        <h2 id="stats-heading" className="sr-only">
          Workspace Statistics
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs flex items-center gap-4 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 flex items-center justify-center font-bold">
              <FileText className="w-6 h-6" aria-hidden="true" />
            </div>
            <div>
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block">Indexed Documents</span>
              <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {loading ? '...' : stats?.total_documents || 168}
              </span>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs flex items-center gap-4 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-400 flex items-center justify-center font-bold">
              <ShieldCheck className="w-6 h-6" aria-hidden="true" />
            </div>
            <div>
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block">Completed Analyses</span>
              <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {loading ? '...' : stats?.total_analyses || 32}
              </span>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs flex items-center gap-4 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 flex items-center justify-center font-bold">
              <Clock className="w-6 h-6" aria-hidden="true" />
            </div>
            <div>
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 block">Pending Reviews</span>
              <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {loading ? '...' : stats?.pending_actions || 3}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Recent Documents & Activity Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Recent Documents */}
        <section aria-labelledby="recent-docs-heading" className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 id="recent-docs-heading" className="text-sm font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
              Recent Documents
            </h2>
            <Link
              href="/documents"
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 inline-flex items-center gap-1 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded p-1"
            >
              <span>View all ({stats?.total_documents || 168})</span>
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {(stats?.recent_documents || []).map((doc) => (
              <DocumentCard key={doc.document_id} document={doc} />
            ))}
          </div>
        </section>

        {/* Right 1 Col: Recent Activity */}
        <section aria-labelledby="recent-activity-heading" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 id="recent-activity-heading" className="text-sm font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
              Recent Activity
            </h2>
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Audit Log
            </span>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 divide-y divide-slate-100 dark:divide-slate-800 shadow-xs transition-colors">
            {(stats?.recent_activity || []).map((act) => (
              <div key={act.event_id} className="py-3 first:pt-0 last:pb-0">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-semibold text-slate-800 dark:text-slate-200">{act.title}</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                    {formatDate(act.timestamp)}
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-1.5">
                  {act.description}
                </p>
                {act.badge && (
                  <span className="inline-block px-1.5 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                    {act.badge}
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
