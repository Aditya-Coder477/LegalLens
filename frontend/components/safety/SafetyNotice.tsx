import React from 'react';
import { ShieldAlert } from 'lucide-react';

export const SafetyNotice: React.FC = () => {
  return (
    <div className="bg-slate-50 border-b border-slate-200 px-4 py-1.5 text-xs text-slate-600 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <ShieldAlert className="w-3.5 h-3.5 text-slate-500" />
        <span>
          <strong>Legal Information Workspace:</strong> LegalLens provides AI-assisted legal research and document analysis. It does not provide legal representation or legal advice.
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-800 border border-purple-200">
          Reference Development Corpus
        </span>
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-800 border border-blue-200">
          Evidence-First AI
        </span>
      </div>
    </div>
  );
};
