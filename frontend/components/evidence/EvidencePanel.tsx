import React from 'react';
import { FileText, ArrowRight, ShieldCheck } from 'lucide-react';
import { RetrievedEvidence } from '../../lib/types';
import { SourceBadge } from '../citations/SourceBadge';

interface EvidencePanelProps {
  evidence: RetrievedEvidence;
  onOpenDocument?: (docId: string, section?: string, page?: number) => void;
  highlight?: boolean;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  evidence,
  onOpenDocument,
  highlight = false,
}) => {
  return (
    <div
      className={`border rounded-lg p-4 transition ${
        highlight
          ? 'bg-blue-50/50 border-blue-300 ring-1 ring-blue-300'
          : 'bg-white border-slate-200 hover:border-slate-300'
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <span className="text-xs font-semibold text-slate-800">
            {evidence.title || evidence.chunk_id}
          </span>
          {evidence.section && (
            <span className="text-[11px] font-medium bg-slate-100 text-slate-700 px-1.5 py-0.2 rounded border border-slate-200">
              Sec: {evidence.section}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-slate-500">
            p. {evidence.page_start || 1}
          </span>
          <SourceBadge authority={evidence.source_authority} synthetic={evidence.synthetic} />
        </div>
      </div>

      <div className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded border border-slate-100 font-serif">
        {evidence.text}
      </div>

      <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-100">
        <div className="flex items-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Relevance Score: {(evidence.score || 0.9).toFixed(2)}</span>
        </div>
        {onOpenDocument && (
          <button
            onClick={() => onOpenDocument(evidence.document_id, evidence.section, evidence.page_start)}
            className="inline-flex items-center gap-1 font-medium text-blue-600 hover:text-blue-800 transition"
          >
            <span>Jump to text</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
};
