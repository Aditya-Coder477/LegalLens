'use client';

import React, { useState } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  FileText,
  UserCheck,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  HelpCircle,
} from 'lucide-react';
import { AIResponse, Citation } from '../../lib/types';
import { CitationBadge } from '../citations/CitationBadge';
import { CitationModal } from '../citations/CitationModal';
import { SourceBadge } from '../citations/SourceBadge';
import { SafetyBanner } from '../safety/SafetyBanner';
import { EvidencePanel } from '../evidence/EvidencePanel';

interface AnswerViewProps {
  response: AIResponse;
  onNavigateToDocument?: (docId: string, section?: string, page?: number) => void;
  onOpenLawyerHandoff?: () => void;
  onOpenHandoff?: () => void;
}

export const AnswerView: React.FC<AnswerViewProps> = ({
  response,
  onNavigateToDocument,
  onOpenLawyerHandoff,
  onOpenHandoff,
}) => {
  const triggerHandoff = onOpenLawyerHandoff || onOpenHandoff;
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [showAllEvidence, setShowAllEvidence] = useState(false);

  // Status mapping with both icon, text, and semantic styling
  const getStatusDisplay = () => {
    switch (response.status) {
      case 'VERIFIED':
        return {
          label: 'Grounded: Strongly supported by retrieved evidence',
          classes: 'text-emerald-800 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-800',
          icon: <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />,
        };
      case 'PARTIALLY_SUPPORTED':
        return {
          label: 'Qualified: Partially supported by evidence',
          classes: 'text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/60 border-amber-300 dark:border-amber-800',
          icon: <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />,
        };
      case 'LIMITED_EVIDENCE':
        return {
          label: 'Caution: Limited evidence found in knowledge base',
          classes: 'text-yellow-800 dark:text-yellow-300 bg-yellow-50 dark:bg-yellow-950/60 border-yellow-300 dark:border-yellow-800',
          icon: <AlertTriangle className="w-4 h-4 shrink-0 text-yellow-600 dark:text-yellow-400" aria-hidden="true" />,
        };
      case 'NO_EVIDENCE':
        return {
          label: 'No Evidence: No sufficient evidence found in selected sources',
          classes: 'text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700',
          icon: <AlertTriangle className="w-4 h-4 shrink-0 text-slate-600 dark:text-slate-400" aria-hidden="true" />,
        };
      case 'CONFLICT':
        return {
          label: 'Conflict: Opposing legal provisions or precedents detected',
          classes: 'text-rose-800 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/60 border-rose-300 dark:border-rose-800',
          icon: <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" aria-hidden="true" />,
        };
      default:
        return {
          label: 'Grounded Legal Information',
          classes: 'text-blue-800 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/60 border-blue-300 dark:border-blue-800',
          icon: <ShieldCheck className="w-4 h-4 shrink-0 text-blue-600 dark:text-blue-400" aria-hidden="true" />,
        };
    }
  };

  const statusInfo = getStatusDisplay();

  return (
    <div className="space-y-6">
      {/* Question Header */}
      <section aria-labelledby="query-heading" className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
        <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">
          Legal Inquiry
        </span>
        <h2 id="query-heading" className="text-base font-bold text-slate-900 dark:text-slate-100">
          {response.query}
        </h2>
      </section>

      {/* Reference Dataset Warning if applicable */}
      {response.synthetic_sources_used && (
        <SafetyBanner
          variant="synthetic"
          title="Reference Development Source"
          message="This explanation was generated from reference development documents. It is provided for legal research and analysis."
        />
      )}

      {/* Safety Flags if detected */}
      {response.safety_flags.length > 0 && (
        <SafetyBanner
          variant="warning"
          title="Advisory Safety Flags"
          message={response.safety_flags.join(' • ')}
        />
      )}

      {/* No Evidence Callout if status is NO_EVIDENCE */}
      {response.status === 'NO_EVIDENCE' && (
        <div
          role="region"
          aria-label="No evidence statement"
          className="p-4 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-100/80 dark:bg-slate-900 space-y-2"
        >
          <div className="flex items-center gap-2 text-slate-800 dark:text-slate-200 font-bold text-xs uppercase tracking-wider">
            <HelpCircle className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <span>No Sufficient Evidence Found</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            The knowledge base and indexed sources do not contain direct statutory provisions or contractual clauses answering this specific query. Consider uploading the contract or broadening search terms.
          </p>
        </div>
      )}

      {/* Primary Answer Card (AI Explanation) */}
      <section aria-labelledby="ai-explanation-heading" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
        <div className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 px-5 py-3 flex flex-wrap items-center justify-between gap-2">
          <h3 id="ai-explanation-heading" className="text-xs font-bold text-slate-700 dark:text-slate-300 tracking-wide uppercase">
            AI Explanation
          </h3>

          <div
            aria-live="polite"
            aria-atomic="true"
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${statusInfo.classes}`}
          >
            {statusInfo.icon}
            <span>{statusInfo.label}</span>
          </div>
        </div>

        <div className="p-6">
          <p className="text-sm leading-relaxed text-slate-800 dark:text-slate-200 font-sans whitespace-pre-wrap">
            {response.direct_answer}
          </p>

          {/* Inline Citations */}
          {response.citations.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
              <span className="font-semibold text-slate-700 dark:text-slate-300">Referenced Citations:</span>
              {response.citations.map((c) => (
                <CitationBadge
                  key={c.citation_id}
                  citation={c}
                  onClick={(cit) => setSelectedCitation(cit)}
                />
              ))}
              <span className="text-xs text-slate-500 dark:text-slate-500 ml-1">(Click to inspect verified provenance)</span>
            </div>
          )}
        </div>
      </section>

      {/* Distinct Section: Supported By Source Evidence */}
      <section aria-labelledby="source-evidence-heading" className="bg-slate-50/60 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 id="source-evidence-heading" className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
              Supported By: Source Evidence
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Verifiable statutory clauses, precedent excerpts, and contractual sections
            </p>
          </div>
          {response.evidence_items.length > 2 && (
            <button
              type="button"
              onClick={() => setShowAllEvidence(!showAllEvidence)}
              aria-expanded={showAllEvidence}
              className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-semibold inline-flex items-center gap-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded p-1"
            >
              <span>{showAllEvidence ? 'Show fewer excerpts' : `View all (${response.evidence_items.length})`}</span>
              {showAllEvidence ? (
                <ChevronUp className="w-3.5 h-3.5" aria-hidden="true" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
              )}
            </button>
          )}
        </div>

        <div className="space-y-3">
          {(showAllEvidence ? response.evidence_items : response.evidence_items.slice(0, 2)).map((ev) => (
            <EvidencePanel
              key={ev.chunk_id}
              evidence={ev}
              onOpenDocument={onNavigateToDocument}
            />
          ))}
        </div>
      </section>

      {/* Extracted Next Steps & Professional Lawyer Handoff */}
      <section aria-labelledby="next-steps-heading" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h3 id="next-steps-heading" className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
            Advocate / Professional Review
          </h3>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            LegalLens provides legal information, not a substitute for professional legal advice. Export a structured dossier with full evidence for an advocate.
          </p>
        </div>

        {triggerHandoff && (
          <button
            type="button"
            onClick={triggerHandoff}
            className="shrink-0 inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
          >
            <UserCheck className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Prepare Lawyer Dossier</span>
          </button>
        )}
      </section>

      {/* Citation Inspector Modal */}
      {selectedCitation && (
        <CitationModal
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
          onNavigateToDocument={onNavigateToDocument}
        />
      )}
    </div>
  );
};
