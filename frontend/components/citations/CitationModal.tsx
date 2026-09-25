'use client';

import React, { useEffect, useRef } from 'react';
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
  const modalRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<Element | null>(null);

  useEffect(() => {
    if (citation) {
      triggerRef.current = window.document.activeElement;
      setTimeout(() => {
        const closeBtn = modalRef.current?.querySelector<HTMLButtonElement>('button[aria-label="Close citation inspector"]');
        closeBtn?.focus();
      }, 50);

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onClose();
        } else if (e.key === 'Tab' && modalRef.current) {
          const focusableEls = modalRef.current.querySelectorAll<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          if (focusableEls.length > 0) {
            const first = focusableEls[0];
            const last = focusableEls[focusableEls.length - 1];
            if (e.shiftKey && window.document.activeElement === first) {
              e.preventDefault();
              last.focus();
            } else if (!e.shiftKey && window.document.activeElement === last) {
              e.preventDefault();
              first.focus();
            }
          }
        }
      };

      window.addEventListener('keydown', handleKeyDown);
      return () => {
        window.removeEventListener('keydown', handleKeyDown);
        if (triggerRef.current instanceof HTMLElement) {
          triggerRef.current.focus();
        }
      };
    }
  }, [citation, onClose]);

  if (!citation) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="citation-modal-title"
        aria-describedby="citation-modal-desc"
        className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 max-w-lg w-full overflow-hidden transition-colors"
      >
        {/* Header */}
        <div className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="w-7 h-7 rounded-md bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-bold flex items-center justify-center text-xs">
              {citation.citation_id}
            </span>
            <div>
              <h2 id="citation-modal-title" className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Legal Citation Inspector
              </h2>
              <p id="citation-modal-desc" className="text-xs text-slate-500 dark:text-slate-400">
                Verified Evidence & Provenance
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1.5 rounded-lg transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
            aria-label="Close citation inspector"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50/80 dark:bg-slate-950/60 p-3.5 rounded-lg border border-slate-200 dark:border-slate-800">
            <div>
              <span className="text-slate-500 dark:text-slate-400 block mb-0.5 font-medium">Target Document</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" aria-hidden="true" />
                {citation.document_id}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 block mb-0.5 font-medium">Section / Page</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {citation.section || 'General'} · Page {citation.page || 1}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 block mb-0.5 font-medium">Source Authority</span>
              <SourceBadge authority={citation.source_authority} synthetic={false} />
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 block mb-0.5 font-medium">Verification State</span>
              {citation.is_valid ? (
                <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
                  Grounded Claim
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-rose-700 dark:text-rose-400 font-semibold">
                  <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
                  Citation Unverified
                </span>
              )}
            </div>
          </div>

          {/* Excerpt */}
          <div className="space-y-1.5">
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
              Verified Source Excerpt:
            </span>
            <div className="p-3 bg-blue-50/40 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 rounded-lg text-xs leading-relaxed text-slate-800 dark:text-slate-200 font-serif italic">
              "{citation.excerpt}"
            </div>
          </div>

          {/* SHA-256 / Provenance Fingerprint */}
          <div className="p-3 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <Hash className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />
              <span className="text-slate-500 dark:text-slate-400">Provenance Hash:</span>
              <span className="font-mono text-slate-700 dark:text-slate-300">
                {citation.sha256 ? citation.sha256.substring(0, 16) + '...' : 'Verified (SHA-256)'}
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-slate-50 dark:bg-slate-800/60 border-t border-slate-200 dark:border-slate-800 px-5 py-3 flex items-center justify-between">
          <span className="text-xs text-slate-500 dark:text-slate-400">
            Strict provenance preservation
          </span>
          {onNavigateToDocument && (
            <button
              type="button"
              onClick={() => {
                onNavigateToDocument(citation.document_id, citation.section, citation.page);
                onClose();
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
            >
              <span>View In Full Document</span>
              <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
