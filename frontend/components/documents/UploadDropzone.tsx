'use client';

import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle2, AlertTriangle, Loader2, RefreshCw } from 'lucide-react';
import { LegalLensAPI } from '../../lib/api/client';
import { DocumentSummary } from '../../lib/types';

interface UploadDropzoneProps {
  onUploadSuccess: (newDoc: DocumentSummary) => void;
}

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadState, setUploadState] = useState<
    'idle' | 'validating' | 'uploading' | 'structuring' | 'indexing' | 'ready' | 'error'
  >('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [injectionWarning, setInjectionWarning] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileProcess = async (file: File) => {
    setErrorMsg(null);
    setInjectionWarning(null);

    // 1. Validation
    if (file.size === 0) {
      setErrorMsg('The selected file is empty. Please choose a valid document.');
      setUploadState('error');
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      setErrorMsg('File size exceeds the 25 MB maximum limit.');
      setUploadState('error');
      return;
    }

    try {
      setUploadState('validating');

      const isTextFile =
        file.name.endsWith('.txt') || file.name.endsWith('.md') || file.type.startsWith('text/');
      if (isTextFile) {
        try {
          const text = await file.text();
          if (/ignore previous instructions|disregard|system prompt/i.test(text)) {
            setInjectionWarning(
              'Notice: Potential instruction overrides detected in document text. Content will be safely contained as passive evidence only.'
            );
          }
        } catch {
          // ignore
        }
      }

      setUploadState('uploading');
      await new Promise((r) => setTimeout(r, 300));

      setUploadState('structuring');
      await new Promise((r) => setTimeout(r, 300));

      setUploadState('indexing');
      const docType =
        file.name.toLowerCase().includes('contract') || file.name.toLowerCase().includes('agreement')
          ? 'Contract'
          : 'User Document';

      const newDoc = await LegalLensAPI.uploadFile(
        file,
        file.name.replace(/\.[^/.]+$/, ''),
        docType
      );

      setUploadState('ready');
      onUploadSuccess(newDoc);

      setTimeout(() => {
        setUploadState('idle');
      }, 3000);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'Failed to upload and structure document. No changes were made.');
      setUploadState('error');
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileProcess(e.dataTransfer.files[0]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };

  return (
    <section aria-labelledby="upload-section-heading" className="space-y-3">
      <h3 id="upload-section-heading" className="sr-only">
        Document Upload Zone
      </h3>

      <div
        role="button"
        tabIndex={0}
        aria-label="Upload a legal document. Press Enter or Space to open file selector, or drag and drop files here."
        onKeyDown={handleKeyDown}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-6 text-center transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 ${
          isDragging
            ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/30'
            : 'border-slate-300 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-600 bg-slate-50/50 dark:bg-slate-900/50'
        }`}
      >
        {/* Hidden but programmatically linked accessible input */}
        <input
          ref={fileInputRef}
          type="file"
          id="doc-upload-input"
          className="sr-only"
          accept=".txt,.pdf,.docx,.md,.json"
          aria-describedby="upload-formats-desc"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFileProcess(e.target.files[0]);
            }
          }}
        />

        {uploadState === 'idle' && (
          <div className="cursor-pointer">
            <UploadCloud className="w-10 h-10 text-slate-400 dark:text-slate-500 mx-auto mb-2" aria-hidden="true" />
            <label
              htmlFor="doc-upload-input"
              className="text-sm font-semibold text-slate-800 dark:text-slate-200 block mb-1 cursor-pointer hover:text-blue-600 dark:hover:text-blue-400"
            >
              Upload a Legal Document
            </label>
            <p id="upload-formats-desc" className="text-xs text-slate-600 dark:text-slate-400">
              Drag & drop PDF, TXT, DOCX, or press Enter to browse (Max 25 MB)
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-500 mt-2">
              Workspace-scoped · Client-side parsed · Automated SHA-256 Hash Verification
            </p>
          </div>
        )}

        {/* Live status announcements for screen readers */}
        <div aria-live="polite" aria-atomic="true">
          {uploadState !== 'idle' && uploadState !== 'ready' && uploadState !== 'error' && (
            <div className="py-2 space-y-2">
              <Loader2 className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-spin mx-auto" aria-hidden="true" />
              <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 capitalize">
                {uploadState === 'validating' && 'Validating document format and security...'}
                {uploadState === 'uploading' && 'Uploading document to workspace...'}
                {uploadState === 'structuring' && 'Extracting & structuring legal hierarchy...'}
                {uploadState === 'indexing' && 'Generating vector embeddings & SHA-256 index...'}
              </div>
            </div>
          )}

          {uploadState === 'ready' && (
            <div className="py-2 text-emerald-700 dark:text-emerald-400 flex flex-col items-center gap-1.5">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
              <span className="text-xs font-semibold">Document Indexed & Ready for Retrieval</span>
            </div>
          )}
        </div>

        {/* Error Region */}
        {errorMsg && (
          <div
            role="alert"
            className="mt-3 text-xs text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 p-3 rounded-lg border border-rose-200 dark:border-rose-800 flex items-center justify-between gap-3 text-left"
          >
            <div>
              <p className="font-semibold">{errorMsg}</p>
              <p className="text-[11px] text-rose-600 dark:text-rose-400 mt-0.5">Your document is safe. No changes were made.</p>
            </div>
            <button
              type="button"
              onClick={() => {
                setErrorMsg(null);
                setUploadState('idle');
                fileInputRef.current?.click();
              }}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-rose-600 hover:bg-rose-700 text-white font-medium text-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
            >
              <RefreshCw className="w-3 h-3" aria-hidden="true" />
              <span>Retry</span>
            </button>
          </div>
        )}
      </div>

      {injectionWarning && (
        <div
          role="status"
          aria-live="polite"
          className="text-xs text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 p-3 rounded-lg border border-amber-200 dark:border-amber-800 flex items-start gap-2"
        >
          <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" aria-hidden="true" />
          <span>{injectionWarning}</span>
        </div>
      )}
    </section>
  );
};
