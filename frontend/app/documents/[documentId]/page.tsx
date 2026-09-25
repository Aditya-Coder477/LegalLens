'use client';

import React, { useEffect, useState, Suspense } from 'react';
import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
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
} from 'lucide-react';
import { LegalLensAPI } from '../../../lib/api/client';
import { DocumentDetail, LegalHierarchyNode } from '../../../lib/types';
import { SourceBadge } from '../../../components/citations/SourceBadge';
import { DocumentViewer } from '../../../components/viewer/DocumentViewer';
import { HierarchyTree } from '../../../components/viewer/HierarchyTree';

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
      {/* Top Navigation & Actions Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
        <div className="flex items-center gap-3">
          <Link
            href="/documents"
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-base font-bold text-slate-900">{document.title}</h1>
              <SourceBadge authority={document.source_authority} synthetic={document.synthetic} />
            </div>
            <p className="text-xs text-slate-500 flex items-center gap-2">
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
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
          >
            <FileCheck className="w-3.5 h-3.5" />
            <span>Summary</span>
          </Link>

          <Link
            href={`/documents/${document.document_id}/clauses`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
          >
            <Scale className="w-3.5 h-3.5" />
            <span>Clauses</span>
          </Link>

          <Link
            href={`/documents/${document.document_id}/obligations`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
          >
            <Shield className="w-3.5 h-3.5" />
            <span>Obligations</span>
          </Link>

          <Link
            href={`/documents/${document.document_id}/deadlines`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Deadlines</span>
          </Link>
        </div>
      </div>

      {/* Main Document Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left Column: Legal Hierarchy Navigation */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-3">
          <div className="flex items-center gap-1.5 pb-2 border-b border-slate-100">
            <FolderTree className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
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
