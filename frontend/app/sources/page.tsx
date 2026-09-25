'use client';

import React, { useEffect, useState } from 'react';
import { Database, ShieldAlert, CheckCircle2, Search, Filter, ExternalLink, Hash, FileText } from 'lucide-react';
import { LegalLensAPI } from '../../lib/api/client';
import { SourceOverview } from '../../lib/types';
import { SourceBadge } from '../../components/citations/SourceBadge';
import { SafetyBanner } from '../../components/safety/SafetyBanner';

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [authorityFilter, setAuthorityFilter] = useState('ALL');

  useEffect(() => {
    async function loadSources() {
      try {
        const data = await LegalLensAPI.getSources();
        setSources(data);
      } catch (err) {
        console.error('Failed to load sources', err);
      } finally {
        setLoading(false);
      }
    }
    loadSources();
  }, []);

  const filtered = sources.filter((s) => {
    const matchesSearch =
      (s.source_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.source_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.source_authority || '').toLowerCase().includes(searchTerm.toLowerCase());

    const matchesAuth =
      authorityFilter === 'ALL' ||
      (authorityFilter === 'SYNTHETIC' && s.synthetic) ||
      (authorityFilter === 'OFFICIAL' && !s.synthetic);

    return matchesSearch && matchesAuth;
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Page Title */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] text-blue-600 font-semibold uppercase tracking-wider">
            Corpus Provenance & Knowledge Base
          </span>
          <span className="text-xs text-slate-400">•</span>
          <span className="text-xs text-slate-500">Legal Authorities Directory</span>
        </div>
        <h1 className="text-xl font-bold text-slate-900">
          Knowledge Base Sources & Statutory Authorities
        </h1>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl">
          Full catalog of ingested Indian statutes, legal codes, court precedents, and development test corpora with cryptographic integrity verification.
        </p>
      </div>

      {/* Reference Corpus Disclaimer Banner */}
      <SafetyBanner
        variant="synthetic"
        title="Reference Corpus Notice"
        message="Development & Demonstration Notice: Records tagged REFERENCE were generated for development, automated retrieval evaluation, and UI testing. They do not constitute official gazettes or legal advice."
      />

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
            Total Ingested Sources
          </span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {sources.length}
          </div>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Statutes, Codes & Contracts</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
            Indexed Legal Chunks
          </span>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {sources.reduce((acc, s) => acc + (s.total_chunks || 0), 0)}
          </div>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Indexed for Hybrid BM25 + Vector Search</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs">
          <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider block">
            Reference Benchmark Ratio
          </span>
          <div className="text-2xl font-black text-amber-900 mt-1">
            {sources.length > 0
              ? Math.round(
                  (sources.filter((s) => s.synthetic).length / sources.length) * 100
                )
              : 0}
            %
          </div>
          <span className="text-[11px] text-amber-700 mt-0.5 block">Explicitly isolated & flagged</span>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white border border-slate-200 rounded-2xl p-3 shadow-xs flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search statutes, document ID, jurisdiction..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
          />
        </div>

        <div className="flex items-center gap-1.5 w-full sm:w-auto">
          {['ALL', 'OFFICIAL', 'SYNTHETIC'].map((auth) => (
            <button
              key={auth}
              onClick={() => setAuthorityFilter(auth)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                authorityFilter === auth
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {auth === 'ALL' ? 'All Sources' : auth === 'OFFICIAL' ? 'Official Legal' : 'Reference Corpus'}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                <th className="py-3 px-4">Authority & Title</th>
                <th className="py-3 px-4">Source ID</th>
                <th className="py-3 px-4">Document Type</th>
                <th className="py-3 px-4">Authority Class</th>
                <th className="py-3 px-4">Chunks</th>
                <th className="py-3 px-4">Disclaimer Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {filtered.map((s) => (
                <tr key={s.source_id} className="hover:bg-slate-50/70 transition">
                  <td className="py-3.5 px-4">
                    <div className="font-bold text-slate-900">{s.source_name}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{s.source_authority}</div>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-[11px] text-slate-600">
                    {s.source_id}
                  </td>
                  <td className="py-3.5 px-4 text-slate-600">
                    {s.document_type}
                  </td>
                  <td className="py-3.5 px-4">
                    <SourceBadge
                      authority={s.source_authority}
                      synthetic={s.synthetic}
                    />
                  </td>
                  <td className="py-3.5 px-4 text-slate-700 font-mono">
                    {s.total_chunks}
                  </td>
                  <td className="py-3.5 px-4 text-slate-500 text-[11px] max-w-xs truncate">
                    {s.disclaimer || 'Official statutory authority'}
                  </td>
                </tr>
              ))}

              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400 text-xs">
                    No sources match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
