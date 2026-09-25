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

  // Status mapping
  const getStatusDisplay = () => {
    switch (response.status) {
      case 'VERIFIED':
        return {
          label: 'Strongly supported by retrieved evidence',
          classes: 'text-emerald-700 bg-emerald-50 border-emerald-200',
          icon: <ShieldCheck className="w-4 h-4" />,
        };
      case 'PARTIALLY_SUPPORTED':
        return {
          label: 'Partially supported by evidence',
          classes: 'text-amber-700 bg-amber-50 border-amber-200',
          icon: <AlertTriangle className="w-4 h-4" />,
        };
      case 'LIMITED_EVIDENCE':
        return {
          label: 'Limited evidence found',
          classes: 'text-yellow-700 bg-yellow-50 border-yellow-200',
          icon: <AlertTriangle className="w-4 h-4" />,
        };
      case 'NO_EVIDENCE':
        return {
          label: 'No sufficient evidence in selected sources',
          classes: 'text-slate-700 bg-slate-100 border-slate-300',
          icon: <AlertTriangle className="w-4 h-4" />,
        };
      case 'CONFLICT':
        return {
          label: 'Conflicting legal provisions detected',
          classes: 'text-rose-700 bg-rose-50 border-rose-200',
          icon: <AlertTriangle className="w-4 h-4" />,
        };
      default:
        return {
          label: 'Verified Legal Information',
          classes: 'text-blue-700 bg-blue-50 border-blue-200',
          icon: <ShieldCheck className="w-4 h-4" />,
        };
    }
  };

  const statusInfo = getStatusDisplay();

  return (
    <div className="space-y-6">
      {/* Question Header */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
          User Query
        </span>
        <h2 className="text-base font-semibold text-slate-900">{response.query}</h2>
      </div>

      {/* Reference Dataset Warning if applicable */}
      {response.synthetic_sources_used && (
        <SafetyBanner
          variant="synthetic"
          title="Reference Development Source"
          message="This explanation was generated from reference test documents created for development. It is not official Indian statute or authoritative legal precedent."
        />
      )}

      {/* Safety Flags if detected */}
      {response.safety_flags.length > 0 && (
        <SafetyBanner
          variant="warning"
          title="Advisory Flags"
          message={response.safety_flags.join(' • ')}
        />
      )}

      {/* Primary Answer Card (AI Explanation) */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="bg-slate-50 border-b border-slate-200 px-5 py-3 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-700 tracking-wide uppercase">
            AI Explanation
          </span>
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusInfo.classes}`}
          >
            {statusInfo.icon}
            {statusInfo.label}
          </span>
        </div>

        <div className="p-6">
          <p className="text-sm leading-relaxed text-slate-800 font-sans whitespace-pre-wrap">
            {response.direct_answer}
          </p>

          {/* Inline Citations */}
          {response.citations.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
              <span className="font-medium text-slate-600">Referenced Citations:</span>
              {response.citations.map((c) => (
                <CitationBadge
                  key={c.citation_id}
                  citation={c}
                  onClick={(cit) => setSelectedCitation(cit)}
                />
              ))}
              <span className="text-[11px] text-slate-400 ml-1">(Click to inspect evidence)</span>
            </div>
          )}
        </div>
      </div>

      {/* Distinct Section: Supported By Source Evidence */}
      <div className="bg-slate-50/60 border border-slate-200 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Supported By: Source Evidence
            </h3>
            <p className="text-xs text-slate-500">
              Exact retrieved statutory and contractual provisions
            </p>
          </div>
          {response.evidence_items.length > 2 && (
            <button
              onClick={() => setShowAllEvidence(!showAllEvidence)}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1"
            >
              <span>{showAllEvidence ? 'Show less' : `View all (${response.evidence_items.length})`}</span>
              {showAllEvidence ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>

        <div className="space-y-3">
          {(showAllEvidence ? response.evidence_items : response.evidence_items.slice(0, 2)).map(
            (ev) => (
              <EvidencePanel
                key={ev.chunk_id}
                evidence={ev}
                onOpenDocument={onNavigateToDocument}
              />
            )
          )}
        </div>
      </div>

      {/* Evidence-based Next Steps */}
      {response.next_steps.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2.5">
            Possible Procedural Next Steps
          </h4>
          <ul className="space-y-2">
            {response.next_steps.map((step, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-xs text-slate-700">
                <CheckCircle2 className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                <span className="leading-relaxed">{step}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Professional Lawyer Handoff Action */}
      <div className="border border-blue-100 bg-blue-50/40 rounded-xl p-4 flex items-center justify-between gap-4">
        <div>
          <h4 className="text-xs font-semibold text-slate-900 mb-0.5">Need Qualified Legal Advice?</h4>
          <p className="text-xs text-slate-600">
            Export a structured handoff dossier summarizing key facts, clauses, and evidence for an advocate.
          </p>
        </div>
        {triggerHandoff && (
          <button
            onClick={triggerHandoff}
            className="inline-flex items-center gap-1.5 text-xs font-semibold bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 px-3.5 py-2 rounded-lg shadow-xs transition flex-shrink-0"
          >
            <UserCheck className="w-4 h-4 text-blue-600" />
            <span>Prepare Lawyer Dossier</span>
          </button>
        )}
      </div>

      {/* Modal for Citation inspection */}
      <CitationModal
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
        onNavigateToDocument={onNavigateToDocument}
      />
    </div>
  );
};
