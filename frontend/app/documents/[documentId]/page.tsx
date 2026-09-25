'use client';

import React, { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import {
  FileText,
  MessageSquareText,
  FileCheck,
  Scale,
  Shield,
  Clock,
  ArrowLeft,
  Loader2,
  FolderTree,
  ArrowLeftRight,
  Sparkles,
} from 'lucide-react';
import { LegalLensAPI } from '../../../lib/api/client';
import { DocumentDetail, LegalHierarchyNode } from '../../../lib/types';
import { SourceBadge } from '../../../components/citations/SourceBadge';

const DocumentViewer = dynamic(
  () => import('../../../components/viewer/DocumentViewer').then((mod) => mod.DocumentViewer),
  {
    loading: () => (
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-12 text-center text-xs text-slate-400">
        Loading document viewer...
      </div>
    ),
    ssr: false,
  }
);

const HierarchyTree = dynamic(
  () => import('../../../components/viewer/HierarchyTree').then((mod) => mod.HierarchyTree),
  { ssr: false }
);

function DocumentDetailPageContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();

  const documentId = params?.documentId as string;
  const initialSection = searchParams.get('sec') || undefined;

  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSection, setSelectedSection] = useState<string | undefined>(initialSection);
  const [targetPage, setTargetPage] = useState<number>(1);

  useEffect(() => {
    if (documentId) {
      LegalLensAPI.getDocument(documentId)
        .then((doc) => {
          setDocument(doc);
          setLoading(false);
        })
        .catch((err) => {
          console.error(err);
          setLoading(false);
        });
    }
  }, [documentId]);

  const handleSelectNode = (node: LegalHierarchyNode) => {
    setSelectedSection(node.title);
    if (node.page) {
      setTargetPage(node.page);
    }
  };

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-400 gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="text-xs">Loading legal document and hierarchy...</span>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
        <h2 className="text-base font-bold text-slate-900 mb-2">Document Not Found</h2>
        <p className="text-xs text-slate-500 mb-4">
          The requested document ID '{documentId}' does not exist in the Knowledge Base.
        </p>
        <Link href="/documents" className="text-xs font-semibold text-blue-600 hover:underline">
          Return to Documents
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-in fade-in duration-200">
      {/* Problem Solving Progression Banner */}
      <div className="bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200/80 dark:border-blue-900/60 rounded-xl px-4 py-2.5 flex items-center justify-between overflow-x-auto text-xs">
        <span className="font-bold text-blue-900 dark:text-blue-300 uppercase tracking-wider text-[11px] whitespace-nowrap mr-2">
          Document Understanding Flow:
        </span>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-600 dark:text-slate-300 font-medium whitespace-nowrap">
          <span className="text-blue-600 dark:text-blue-400 font-bold">1. Document</span>
          <span className="text-slate-400" aria-hidden="true">→</span>
          <Link href={`/documents/${document.document_id}/summary`} className="hover:text-blue-600 dark:hover:text-blue-400 hover:underline">2. Summary</Link>
          <span className="text-slate-400" aria-hidden="true">→</span>
          <Link href={`/documents/${document.document_id}/clauses`} className="hover:text-blue-600 dark:hover:text-blue-400 hover:underline">3. Clauses</Link>
          <span className="text-slate-400" aria-hidden="true">→</span>
          <Link href={`/documents/${document.document_id}/obligations`} className="hover:text-blue-600 dark:hover:text-blue-400 hover:underline">4. Obligations</Link>
          <span className="text-slate-400" aria-hidden="true">→</span>
          <Link href={`/documents/${document.document_id}/deadlines`} className="hover:text-blue-600 dark:hover:text-blue-400 hover:underline">5. Deadlines</Link>
          <span className="text-slate-400" aria-hidden="true">→</span>
          <Link href={`/documents/${document.document_id}/ask`} className="hover:text-blue-600 dark:hover:text-blue-400 hover:underline">6. Ask Questions</Link>
          <span className="text-slate-400" aria-hidden="true">→</span>
          <span className="text-emerald-700 dark:text-emerald-400 font-semibold">7. Evidence</span>
        </div>
      </div>

      {/* Top Navigation & Actions Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-xs">
        <div className="flex items-center gap-3">
          <Link
            href="/documents"
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-base font-bold text-slate-900 dark:text-slate-100">{document.title}</h1>
              <SourceBadge authority={document.source_authority} synthetic={document.synthetic} />
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-2">
              <span>{document.document_type}</span>
              <span>•</span>
              <span>{document.chunk_count} structured retrieval chunks</span>
              <span>•</span>
              <span>{document.page_count} pages</span>
            </p>
          </div>
        </div>

        {/* Feature Actions */}
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/documents/${document.document_id}/ask`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white transition shadow-xs"
          >
            <MessageSquareText className="w-3.5 h-3.5" />
            <span>Ask Document</span>
          </Link>

          <Link
            href={`/documents/${document.document_id}/summary`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
          >
            <FileCheck className="w-3.5 h-3.5" />
            <span>Summary</span>
          </Link>

          <Link
            href={`/documents/${document.document_id}/clauses`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
          >
            <Scale className="w-3.5 h-3.5" />
            <span>Clauses</span>
          </Link>

          <Link
            href={`/documents/${document.document_id}/obligations`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
          >
            <Shield className="w-3.5 h-3.5" />
            <span>Obligations</span>
          </Link>

          <Link
            href={`/documents/${document.document_id}/deadlines`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Deadlines</span>
          </Link>

          <Link
            href={`/compare`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
          >
            <ArrowLeftRight className="w-3.5 h-3.5" />
            <span>Compare</span>
          </Link>
        </div>
      </div>

      {/* Main Document Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left Column: Legal Hierarchy Navigation */}
        <div className="lg:col-span-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-xs space-y-3">
          <div className="flex items-center gap-1.5 pb-2 border-b border-slate-100 dark:border-slate-800">
            <FolderTree className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
              Legal Hierarchy
            </span>
          </div>

          <div className="max-h-[550px] overflow-y-auto pr-1">
            {document.hierarchy && document.hierarchy.length > 0 ? (
              <HierarchyTree
                nodes={document.hierarchy}
                selectedId={selectedSection}
                onSelectNode={handleSelectNode}
              />
            ) : (
              <span className="text-xs text-slate-400 italic">No hierarchy available.</span>
            )}
          </div>
        </div>

        {/* Right 3 Columns: Document Viewer */}
        <div className="lg:col-span-3">
          <DocumentViewer
            text={document.raw_text || 'No document text content available.'}
            title={document.title}
            currentPage={targetPage}
            totalPages={document.page_count}
            targetSection={selectedSection}
          />
        </div>
      </div>
    </div>
  );
}

export default function DocumentDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center text-xs text-slate-500">
          Loading document viewer...
        </div>
      }
    >
      <DocumentDetailPageContent />
    </Suspense>
  );
}
