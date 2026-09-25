'use client';

import React, { useState, useEffect, useRef } from 'react';
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
  const modalRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<Element | null>(null);

  useEffect(() => {
    if (isOpen) {
      triggerRef.current = window.document.activeElement;
      // Focus modal on open
      setTimeout(() => {
        const closeBtn = modalRef.current?.querySelector<HTMLButtonElement>('button[aria-label="Close dialog"]');
        closeBtn?.focus();
      }, 50);

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onClose();
        } else if (e.key === 'Tab' && modalRef.current) {
          // Trap focus inside modal
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
        // Return focus to trigger element on close
        if (triggerRef.current instanceof HTMLElement) {
          triggerRef.current.focus();
        }
      };
    }
  }, [isOpen, onClose]);

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
        aria-labelledby="lawyer-handoff-title"
        aria-describedby="lawyer-handoff-desc"
        className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 max-w-2xl w-full overflow-hidden flex flex-col max-h-[85vh] transition-colors"
      >
        {/* Header */}
        <div className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 px-5 py-4 flex items-center justify-between">
          <div>
            <h2 id="lawyer-handoff-title" className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Prepare Lawyer Intake Dossier
            </h2>
            <p id="lawyer-handoff-desc" className="text-xs text-slate-500 dark:text-slate-400">
              Structured matter summary with verifiable statutory citations for advocate review.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 transition"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Advisory Warning */}
        <div className="bg-amber-50 dark:bg-amber-950/40 border-b border-amber-200 dark:border-amber-800 px-5 py-2.5 flex items-center gap-2 text-xs text-amber-800 dark:text-amber-300">
          <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>
            Intake preparation aid only. Legal information, not a substitute for professional legal counsel.
          </span>
        </div>

        {/* Dossier Code Text Area */}
        <div className="p-5 flex-1 overflow-y-auto">
          <label htmlFor="dossier-preview-text" className="sr-only">
            Compiled Lawyer Dossier Text
          </label>
          <textarea
            id="dossier-preview-text"
            readOnly
            value={dossierText}
            className="w-full h-80 font-mono text-xs p-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-200 resize-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          />
        </div>

        {/* Actions Footer */}
        <div className="bg-slate-50 dark:bg-slate-800/60 border-t border-slate-200 dark:border-slate-800 px-5 py-3 flex items-center justify-between">
          <span className="text-xs text-slate-500 dark:text-slate-400">Ready to export or print</span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrint}
              aria-label="Print lawyer dossier"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
            >
              <Printer className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Print</span>
            </button>

            <button
              type="button"
              onClick={handleCopy}
              aria-label={copied ? 'Dossier copied to clipboard' : 'Copy dossier to clipboard'}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-xs font-semibold text-white shadow-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Copy Dossier</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
