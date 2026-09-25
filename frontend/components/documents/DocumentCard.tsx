import React from 'react';
import Link from 'next/link';
import { FileText, ArrowRight, MessageSquareText, FileSearch, Layers } from 'lucide-react';
import { DocumentSummary } from '../../lib/types';
import { SourceBadge } from '../citations/SourceBadge';
import { formatDate } from '../../lib/utils/cn';

interface DocumentCardProps {
  document: DocumentSummary;
}

export const DocumentCard: React.FC<DocumentCardProps> = ({ document }) => {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md hover:border-slate-300 transition flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-3 mb-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center flex-shrink-0">
            <FileText className="w-4 h-4" />
          </div>
          <SourceBadge authority={document.source_authority} synthetic={document.synthetic} />
        </div>

        <Link
          href={`/documents/${document.document_id}`}
          className="font-semibold text-sm text-slate-900 hover:text-blue-700 transition line-clamp-2 mb-2"
        >
          {document.title}
        </Link>

        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mb-4">
          <span className="font-medium text-slate-700">{document.document_type}</span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            {document.chunk_count} chunks
          </span>
          <span>•</span>
          <span>{document.page_count} pages</span>
        </div>

        {document.sha256 && (
          <div className="text-[10px] text-slate-400 font-mono truncate mb-3 bg-slate-50 p-1.5 rounded border border-slate-100">
            SHA: {document.sha256.slice(0, 16)}...
          </div>
        )}
      </div>

      <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
        <span className="text-[11px] text-slate-400">
          {formatDate(document.created_at)}
        </span>
        <div className="flex items-center gap-2">
          <Link
            href={`/documents/${document.document_id}/ask`}
            className="text-slate-600 hover:text-blue-700 p-1 rounded hover:bg-slate-50 transition"
            title="Ask about this document"
          >
            <MessageSquareText className="w-4 h-4" />
          </Link>
          <Link
            href={`/documents/${document.document_id}`}
            className="inline-flex items-center gap-1 font-medium text-blue-600 hover:text-blue-800 transition"
          >
            <span>Open</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </div>
  );
};
