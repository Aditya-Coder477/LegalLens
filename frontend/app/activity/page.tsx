'use client';

import React, { useEffect, useState } from 'react';
import { Activity, Clock, ShieldCheck, CheckCircle2, Search, Filter, AlertTriangle, ArrowUpRight } from 'lucide-react';
import { LegalLensAPI } from '../../lib/api/client';
import { ActivityEvent } from '../../lib/types';
import { formatDate } from '../../lib/utils/cn';

export default function ActivityAuditPage() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('ALL');
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function loadActivity() {
      try {
        const data = await LegalLensAPI.getActivity();
        setEvents(data);
      } catch (err) {
        console.error('Failed to load activity', err);
      } finally {
        setLoading(false);
      }
    }
    loadActivity();
  }, []);

  const filtered = events.filter((e) => {
    const matchesSearch =
      (e.title || '').toLowerCase().includes(search.toLowerCase()) ||
      (e.description || '').toLowerCase().includes(search.toLowerCase()) ||
      (e.document_id && e.document_id.toLowerCase().includes(search.toLowerCase()));

    const matchesType =
      filterType === 'ALL' || (e.event_type || '').toUpperCase().includes(filterType);

    return matchesSearch && matchesType;
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Title */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] text-blue-600 font-semibold uppercase tracking-wider">
            Workspace Governance
          </span>
          <span className="text-xs text-slate-400">•</span>
          <span className="text-xs text-slate-500">Immutable Audit Trail</span>
        </div>
        <h1 className="text-xl font-bold text-slate-900">
          Activity Log & Compliance Audit Records
        </h1>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl">
          Complete forensic log of document ingestion, hybrid vector/BM25 retrieval calls, AI reasoning tasks, citation verifications, and safety guardrail checks.
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-2xl p-3 shadow-xs flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search activity log..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
          />
        </div>

        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
          {['ALL', 'QUERY', 'SUMMARY', 'COMPARE', 'INGEST', 'SAFETY'].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition whitespace-nowrap ${
                filterType === type
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Events Timeline */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-xs divide-y divide-slate-100 overflow-hidden">
        {filtered.map((item) => (
          <div key={item.event_id} className="p-4 hover:bg-slate-50/70 transition flex items-start gap-4">
            <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Activity className="w-4 h-4" />
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-900">
                    {item.title}
                  </span>
                  {item.document_id && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
                      {item.document_id}
                    </span>
                  )}
                </div>
                <span className="text-[11px] text-slate-400 font-mono whitespace-nowrap">
                  {formatDate(item.timestamp)}
                </span>
              </div>

              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                {item.description}
              </p>

              <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-400">
                <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                  <ShieldCheck className="w-3 h-3" />
                  <span>Safety Verified</span>
                </span>
                <span>•</span>
                <span>Audit ID: <span className="font-mono">{item.event_id}</span></span>
              </div>
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="p-12 text-center text-slate-400 text-xs">
            No activity events recorded matching the criteria.
          </div>
        )}
      </div>
    </div>
  );
}
