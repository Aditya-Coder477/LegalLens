import React, { useState } from 'react';
import { Search, Copy, Check, ZoomIn, ZoomOut } from 'lucide-react';

interface DocumentViewerProps {
  text: string;
  title: string;
  currentPage?: number;
  totalPages?: number;
  highlightQuery?: string;
  targetSection?: string;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  text,
  title,
  currentPage = 1,
  totalPages = 1,
  highlightQuery,
  targetSection,
}) => {
  const [searchTerm, setSearchTerm] = useState(highlightQuery || '');
  const [fontSize, setFontSize] = useState<number>(14);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Basic search highlight helper
  const renderHighlightedContent = (rawText: string) => {
    if (!searchTerm.trim()) {
      return rawText;
    }

    try {
      const parts = rawText.split(new RegExp(`(${searchTerm})`, 'gi'));
      return parts.map((part, i) =>
        part.toLowerCase() === searchTerm.toLowerCase() ? (
          <mark key={i} className="bg-yellow-200 text-slate-900 rounded-xs px-0.5 font-medium">
            {part}
          </mark>
        ) : (
          part
        )
      );
    } catch {
      return rawText;
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs flex flex-col h-full min-h-[600px]">
      {/* Controls Bar */}
      <div className="bg-slate-50 border-b border-slate-200 px-4 py-2.5 flex items-center justify-between text-xs gap-3">
        <div className="flex items-center gap-2 flex-1 max-w-sm">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search in document..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white pl-8 pr-3 py-1 rounded-md border border-slate-200 text-xs focus:outline-hidden focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-md px-1.5 py-0.5">
            <button
              onClick={() => setFontSize((s) => Math.max(12, s - 1))}
              className="p-1 hover:text-blue-600 transition"
              title="Decrease font size"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[11px] text-slate-500 font-mono px-1">{fontSize}px</span>
            <button
              onClick={() => setFontSize((s) => Math.min(20, s + 1))}
              className="p-1 hover:text-blue-600 transition"
              title="Increase font size"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 px-2 py-1 rounded-md transition"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Target Section Banner */}
      {targetSection && (
        <div className="bg-blue-50 border-b border-blue-200 px-4 py-1.5 text-xs text-blue-900 flex items-center justify-between">
          <span>Active Citation Focus: <strong>{targetSection}</strong></span>
          <span className="text-[10px] text-blue-700">Verified Evidence Target</span>
        </div>
      )}

      {/* Document Text Area */}
      <div className="flex-1 p-6 overflow-y-auto bg-white">
        <div
          className="max-w-3xl mx-auto font-serif leading-relaxed text-slate-800 whitespace-pre-wrap select-text"
          style={{ fontSize: `${fontSize}px` }}
        >
          {renderHighlightedContent(text)}
        </div>
      </div>

      {/* Footer Page Bar */}
      <div className="bg-slate-50 border-t border-slate-200 px-4 py-2 flex items-center justify-between text-xs text-slate-500">
        <span>{title}</span>
        <span>
          Page {currentPage} of {totalPages}
        </span>
      </div>
    </div>
  );
};
