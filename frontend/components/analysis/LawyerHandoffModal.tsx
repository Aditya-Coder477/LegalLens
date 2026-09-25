import React, { useState } from 'react';
import { X, Copy, Check, Printer, AlertCircle } from 'lucide-react';
import { AIResponse, DocumentDetail } from '../../lib/types';

interface LawyerHandoffModalProps {
  isOpen: boolean;
  onClose: () => void;
  response?: AIResponse | null;
  document?: DocumentDetail | null;
}

export const LawyerHandoffModal: React.FC<LawyerHandoffModalProps> = ({
  isOpen,
  onClose,
  response,
  document,
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const dossierText = `LEGALLENS — LAWYER HANDOFF DOSSIER
==================================================
Date: ${new Date().toLocaleDateString('en-IN')}
Corpus: ${document?.synthetic ? 'REFERENCE BENCHMARK CORPUS' : 'USER WORKSPACE'}

MATTER SUMMARY:
${response?.query || 'General Legal Document Review'}

DOCUMENT REFERENCES:
- Document: ${document?.title || response?.citations[0]?.document_id || 'Referenced Document'}
- SHA-256: ${document?.sha256 || 'f2f296ad043f7f4a...'}
- Source Authority: ${document?.source_authority || 'REFERENCE_CORPUS'}

CORE LEGAL CLAUSES & EVIDENCE:
${response?.citations.map((c, i) => `[${i + 1}] ${c.document_id} ${c.section || ''} (p.${c.page || 1}): "${c.excerpt || ''}"`).join('\n') || 'None recorded'}

EXTRACTED NEXT STEPS / ISSUES:
${response?.next_steps.map((s, i) => `${i + 1}. ${s}`).join('\n') || 'Review statutory terms'}

NOTICE TO ADVOCATE / COUNSEL:
This dossier was automatically compiled by the LegalLens Legal Intelligence Assistant to facilitate attorney-client intake. It does NOT constitute legal advice, advocate work product, or formal legal opinion.
==================================================`;

  const handleCopy = () => {
    navigator.clipboard.writeText(dossierText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-2xl w-full overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="bg-slate-50 border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Lawyer Discussion Dossier</h3>
            <p className="text-xs text-slate-500">Structured legal matter intake summary</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Notice */}
        <div className="bg-amber-50 border-b border-amber-200 px-5 py-2.5 flex items-start gap-2 text-xs text-amber-900">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <span>
            <strong>Attorney Review Only:</strong> AI-generated summary intended to prepare you for discussion with a certified advocate.
          </span>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 font-mono text-xs bg-slate-50/50 leading-relaxed text-slate-800 whitespace-pre-wrap select-all">
          {dossierText}
        </div>

        {/* Footer */}
        <div className="bg-slate-50 border-t border-slate-200 px-5 py-3.5 flex items-center justify-between">
          <button
            onClick={onClose}
            className="text-xs font-medium text-slate-600 hover:text-slate-900 transition"
          >
            Close
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="inline-flex items-center gap-1.5 text-xs font-medium bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 px-3 py-1.5 rounded-lg transition"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print</span>
            </button>
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white px-3.5 py-1.5 rounded-lg shadow-xs transition"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Dossier'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
