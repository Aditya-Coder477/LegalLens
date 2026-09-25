'use client';

import React, { useEffect, useState } from 'react';
import { Search, Filter, Plus, Files, ArrowUpDown, Loader2 } from 'lucide-react';
import { LegalLensAPI } from '../../lib/api/client';
import { DocumentSummary } from '../../lib/types';
import { DocumentCard } from '../../components/documents/DocumentCard';
import { UploadDropzone } from '../../components/documents/UploadDropzone';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    LegalLensAPI.getDocuments()
      .then((data) => {
        setDocuments(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load documents:', err);
        setLoading(false);
      });
  }, []);

  const handleUploadSuccess = (newDoc: DocumentSummary) => {
    setDocuments((prev) => [newDoc, ...prev]);
    setShowUpload(false);
  };

  const filteredDocs = documents.filter((doc) => {
    const matchesSearch =
      doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.document_id.toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;

    if (selectedType === 'ALL') return true;
    if (selectedType === 'CONTRACT') return doc.document_type === 'Contract';
    if (selectedType === 'ACT') return doc.document_type === 'Act';
    if (selectedType === 'RULE') return doc.document_type === 'Rule';
    if (selectedType === 'JUDGMENT') return doc.document_type === 'Judgment';
    if (selectedType === 'USER') return doc.source_authority === 'USER_DOCUMENT';

    return true;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Page Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Legal Documents Repository</h1>
          <p className="text-xs text-slate-500">
            Search, analyze, and inspect structured legal units across statutory, reference, and user-provided corpuses.
          </p>
        </div>

        <button
          onClick={() => setShowUpload(!showUpload)}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition self-start"
        >
          <Plus className="w-4 h-4" />
          <span>{showUpload ? 'Hide Upload' : 'Upload Document'}</span>
        </button>
      </div>

      {/* Upload Dropzone Collapse */}
      {showUpload && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <UploadDropzone onUploadSuccess={handleUploadSuccess} />
        </div>
      )}

      {/* Filters and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-xs">
        <div className="relative w-full sm:max-w-xs">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by title or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-50 pl-9 pr-3 py-1.5 rounded-lg border border-slate-200 text-xs focus:outline-hidden focus:ring-1 focus:ring-blue-600"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
          <span className="text-xs text-slate-400 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" />
            Type:
          </span>
          {['ALL', 'CONTRACT', 'ACT', 'RULE', 'JUDGMENT', 'USER'].map((t) => (
            <button
              key={t}
              onClick={() => setSelectedType(t)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
                selectedType === t
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
              }`}
            >
              {t === 'ALL' ? 'All' : t.charAt(0) + t.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Document Grid */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-slate-400 gap-2">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <span className="text-xs">Loading legal documents...</span>
        </div>
      ) : filteredDocs.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredDocs.map((doc) => (
            <DocumentCard key={doc.document_id} document={doc} />
          ))}
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
          <Files className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-800 mb-1">No documents found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
            No legal documents matched your search filter. Try clearing the filter or uploading a new document.
          </p>
          <button
            onClick={() => {
              setSearchTerm('');
              setSelectedType('ALL');
            }}
            className="text-xs text-blue-600 hover:underline font-medium"
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  );
}
