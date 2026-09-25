'use client';

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
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs flex flex-col h-full min-h-[600px] transition-colors">
      {/* Controls Bar */}
      <div className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 px-4 py-2.5 flex items-center justify-between text-xs gap-3">
        <div className="flex items-center gap-2 flex-1 max-w-sm">
          <form role="search" aria-label="Search within document text" className="relative w-full">
            <label htmlFor="doc-viewer-search" className="sr-only">
              Search text within document
            </label>
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" aria-hidden="true" />
            <input
              id="doc-viewer-search"
              type="text"
              placeholder="Search in document..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white dark:bg-slate-900 pl-8 pr-3 py-1 rounded-md border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            />
          </form>
        </div>

        <div className="flex items-center gap-3">
          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-1.5 py-0.5">
            <button
              type="button"
              onClick={() => setFontSize((s) => Math.max(12, s - 1))}
              className="p-1 hover:text-blue-600 dark:hover:text-blue-400 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
              aria-label="Decrease text size"
              title="Decrease font size"
            >
              <ZoomOut className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
            <span aria-label={`Font size ${fontSize} pixels`} className="text-xs text-slate-500 dark:text-slate-400 font-mono px-1">
              {fontSize}px
            </span>
            <button
              type="button"
              onClick={() => setFontSize((s) => Math.min(20, s + 1))}
              className="p-1 hover:text-blue-600 dark:hover:text-blue-400 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
              aria-label="Increase text size"
              title="Increase font size"
            >
              <ZoomIn className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>

          <button
            type="button"
            onClick={handleCopy}
            aria-label={copied ? 'Document text copied' : 'Copy document text'}
            className="inline-flex items-center gap-1 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 px-2 py-1 rounded-md transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            {copied ? (
              <Check className="w-3 h-3 text-emerald-600" aria-hidden="true" />
            ) : (
              <Copy className="w-3 h-3" aria-hidden="true" />
            )}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Target Section Banner */}
      {targetSection && (
        <div
          role="status"
          aria-live="polite"
          className="bg-blue-50 dark:bg-blue-950/60 border-b border-blue-200 dark:border-blue-900 px-4 py-2 text-xs text-blue-800 dark:text-blue-200 flex items-center justify-between"
        >
          <span>
            Target Section: <strong>{targetSection}</strong>
          </span>
          <span className="text-xs text-blue-600 dark:text-blue-400">
            Page {currentPage} of {totalPages}
          </span>
        </div>
      )}

      {/* Document Content View */}
      <div className="flex-1 p-6 overflow-y-auto font-mono text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">
        <div style={{ fontSize: `${fontSize}px` }}>
          {renderHighlightedContent(text)}
        </div>
      </div>

      {/* Footer Navigation Bar */}
      <div className="bg-slate-50 dark:bg-slate-800/60 border-t border-slate-200 dark:border-slate-800 px-4 py-2 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{title}</span>
        <span aria-label={`Showing page ${currentPage} of total ${totalPages} pages`}>
          Page {currentPage} of {totalPages}
        </span>
      </div>
    </div>
  );
};
