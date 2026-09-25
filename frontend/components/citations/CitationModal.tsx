import React from 'react';
import { X, CheckCircle2, FileText, Hash, ExternalLink, AlertCircle } from 'lucide-react';
import { Citation } from '../../lib/types';
import { SourceBadge } from './SourceBadge';

interface CitationModalProps {
  citation: Citation | null;
  onClose: () => void;
  onNavigateToDocument?: (documentId: string, section?: string, page?: number) => void;
}

export const CitationModal: React.FC<CitationModalProps> = ({
  citation,
  onClose,
  onNavigateToDocument,
}) => {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="bg-slate-50 border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="w-7 h-7 rounded-md bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-xs">
              {citation.citation_id}
            </span>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Legal Citation Inspector</h3>
              <p className="text-xs text-slate-500">Verified Evidence & Provenance</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50/80 p-3.5 rounded-lg border border-slate-200">
            <div>
              <span className="text-slate-400 block mb-0.5">Target Document</span>
              <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                {citation.document_id}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Section / Page</span>
              <span className="font-semibold text-slate-800">
                {citation.section || 'General'} · Page {citation.page || 1}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Source Authority</span>
              <SourceBadge authority={citation.source_authority} synthetic={citation.synthetic} />
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Integrity Verification</span>
              <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {citation.hash_matched ? 'SHA-256 Verified' : 'Standard'}
              </span>
            </div>
          </div>

          {/* Excerpt */}
          <div>
            <span className="text-xs font-semibold text-slate-700 block mb-1.5 uppercase tracking-wider">
              Exact Supporting Excerpt
            </span>
            <div className="p-3 bg-blue-50/40 border border-blue-100 rounded-lg text-xs leading-relaxed text-slate-800 italic">
              "{citation.excerpt || 'Excerpt text preserved in Knowledge Base.'}"
            </div>
          </div>

          {/* Provenance SHA */}
          {citation.sha256 && (
            <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono bg-slate-100/80 px-2.5 py-1.5 rounded border border-slate-200 overflow-x-auto">
              <Hash className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" />
              <span className="truncate">SHA-256: {citation.sha256}</span>
            </div>
          )}

          {/* Disclaimer if reference data */}
          {citation.synthetic && (
            <div className="flex items-start gap-2 text-xs text-purple-700 bg-purple-50 p-2.5 rounded border border-purple-200">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Reference Test Data:</strong> This citation refers to a reference enactment created for evaluation and development. It is not an official Indian statutory citation.
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-slate-50 border-t border-slate-200 px-5 py-3.5 flex items-center justify-between">
          <button
            onClick={onClose}
            className="text-xs font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded transition"
          >
            Close
          </button>
          {onNavigateToDocument && (
            <button
              onClick={() => {
                onNavigateToDocument(citation.document_id, citation.section, citation.page);
                onClose();
              }}
              className="inline-flex items-center gap-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white px-3.5 py-1.5 rounded-lg shadow-xs transition"
            >
              <span>View Source Document</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
