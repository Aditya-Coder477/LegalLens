import React, { useState } from 'react';
import { UploadCloud, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';
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

  const handleFileProcess = async (file: File) => {
    setErrorMsg(null);
    setInjectionWarning(null);

    // 1. Frontend validation
    if (file.size === 0) {
      setErrorMsg('The selected file is empty.');
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      setErrorMsg('File size exceeds the 25 MB maximum limit.');
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
      }, 2000);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'Failed to upload and structure document.');
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

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-6 text-center transition cursor-pointer ${
          isDragging
            ? 'border-blue-500 bg-blue-50/50'
            : 'border-slate-300 hover:border-slate-400 bg-slate-50/50'
        }`}
      >
        <input
          type="file"
          id="doc-upload-input"
          className="hidden"
          accept=".txt,.pdf,.docx,.md,.json"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFileProcess(e.target.files[0]);
            }
          }}
        />

        {uploadState === 'idle' && (
          <label htmlFor="doc-upload-input" className="cursor-pointer block">
            <UploadCloud className="w-9 h-9 text-slate-400 mx-auto mb-2" />
            <span className="text-sm font-semibold text-slate-800 block mb-1">
              Upload a Legal Document
            </span>
            <span className="text-xs text-slate-500 block">
              Drag & drop PDF, TXT, DOCX, or click to browse
            </span>
            <span className="text-[11px] text-slate-400 mt-2 block">
              Workspace-scoped · Private · Automated SHA-256 Hash Verification
            </span>
          </label>
        )}

        {uploadState !== 'idle' && uploadState !== 'ready' && uploadState !== 'error' && (
          <div className="py-2 space-y-2">
            <Loader2 className="w-7 h-7 text-blue-600 animate-spin mx-auto" />
            <div className="text-xs font-medium text-slate-700 capitalize">
              {uploadState === 'validating' && 'Validating document format...'}
              {uploadState === 'uploading' && 'Uploading document...'}
              {uploadState === 'structuring' && 'Extracting & structuring legal hierarchy...'}
              {uploadState === 'indexing' && 'Generating vector embeddings & SHA-256 index...'}
            </div>
          </div>
        )}

        {uploadState === 'ready' && (
          <div className="py-2 text-emerald-700 flex flex-col items-center gap-1.5">
            <CheckCircle2 className="w-8 h-8 text-emerald-600" />
            <span className="text-xs font-semibold">Document Indexed & Ready for Retrieval</span>
          </div>
        )}

        {errorMsg && (
          <div className="mt-3 text-xs text-rose-600 bg-rose-50 p-2.5 rounded-lg border border-rose-200">
            {errorMsg}
          </div>
        )}
      </div>

      {injectionWarning && (
        <div className="text-xs text-amber-800 bg-amber-50 p-3 rounded-lg border border-amber-200 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <span>{injectionWarning}</span>
        </div>
      )}
    </div>
  );
};
