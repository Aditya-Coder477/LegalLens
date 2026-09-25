import React from 'react';
import { Citation } from '../../lib/types';
import { cn } from '../../lib/utils/cn';

interface CitationBadgeProps {
  citation: Citation;
  onClick?: (citation: Citation) => void;
  className?: string;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  citation,
  onClick,
  className,
}) => {
  return (
    <button
      type="button"
      onClick={() => onClick && onClick(citation)}
      className={cn(
        'inline-flex items-center justify-center px-1.5 py-0.2 mx-0.5 rounded text-[11px] font-semibold tracking-wide border transition select-none cursor-pointer',
        citation.is_valid
          ? 'bg-blue-50 text-blue-700 border-blue-300 hover:bg-blue-100 hover:border-blue-400'
          : 'bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100',
        className
      )}
      title={`Citation ${citation.citation_id}: ${citation.document_id} ${citation.section || ''} (Click to inspect evidence)`}
    >
      [{citation.citation_id}]
    </button>
  );
};
