'use client';

import React, { useState } from 'react';
import { Settings, Shield, Database, Lock, Server, CheckCircle2, Sliders, AlertCircle } from 'lucide-react';
import { SafetyNotice } from '../../components/safety/SafetyNotice';

export default function SettingsPage() {
  const [retrievalMode, setRetrievalMode] = useState('hybrid');
  const [safetyThreshold, setSafetyThreshold] = useState('strict');
  const [watermarkSynthetic, setWatermarkSynthetic] = useState(true);
  const [localCacheOnly, setLocalCacheOnly] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Title */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] text-blue-600 font-semibold uppercase tracking-wider">
            Workspace Configuration
          </span>
          <span className="text-xs text-slate-400">•</span>
          <span className="text-xs text-slate-500">Legal Intelligence Preferences</span>
        </div>
        <h1 className="text-xl font-bold text-slate-900">
          Settings & Compliance Guardrails
        </h1>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl">
          Control safety enforcement thresholds, hybrid retrieval pipeline parameters, and workspace data protection policies.
        </p>
      </div>

      {saved && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>Workspace preferences saved successfully.</span>
        </div>
      )}

      {/* Settings Sections */}
      <div className="space-y-4">
        {/* Safety & Grounding */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <Shield className="w-4 h-4 text-blue-600" />
            <span>Safety & Evidence Grounding</span>
          </div>

          <div className="space-y-3 pt-1">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-xs font-semibold text-slate-800 block">
                  Strict Grounding & Citation Validation
                </label>
                <p className="text-[11px] text-slate-500">
                  Refuse or flag responses that cannot be substantiated by knowledge base chunks.
                </p>
              </div>
              <select
                value={safetyThreshold}
                onChange={(e) => setSafetyThreshold(e.target.value)}
                className="text-xs border border-slate-200 rounded-lg px-3 py-1.5 bg-slate-50 text-slate-800 font-medium focus:outline-hidden focus:border-blue-500"
              >
                <option value="strict">Strict (Zero Unverified Claims)</option>
                <option value="standard">Standard (Flag Warnings)</option>
              </select>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100">
              <div>
                <label className="text-xs font-semibold text-slate-800 block">
                  Mandatory Reference Corpus Watermark
                </label>
                <p className="text-[11px] text-slate-500">
                  Always display REFERENCE badges and disclaimers on test legal documents.
                </p>
              </div>
              <input
                type="checkbox"
                checked={watermarkSynthetic}
                onChange={(e) => setWatermarkSynthetic(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Retrieval Engine */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <Sliders className="w-4 h-4 text-blue-600" />
            <span>Hybrid Retrieval Pipeline</span>
          </div>

          <div className="space-y-3 pt-1">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-xs font-semibold text-slate-800 block">
                  Search & Ranking Strategy
                </label>
                <p className="text-[11px] text-slate-500">
                  Combines dense semantic vectors with BM25 keyword matching via Reciprocal Rank Fusion.
                </p>
              </div>
              <select
                value={retrievalMode}
                onChange={(e) => setRetrievalMode(e.target.value)}
                className="text-xs border border-slate-200 rounded-lg px-3 py-1.5 bg-slate-50 text-slate-800 font-medium focus:outline-hidden focus:border-blue-500"
              >
                <option value="hybrid">Hybrid (Dense + BM25 + Cross-Encoder Rerank)</option>
                <option value="dense">Dense Vector Only</option>
                <option value="bm25">BM25 Keyword Only</option>
              </select>
            </div>
          </div>
        </div>

        {/* Data Privacy & Sovereign Storage */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <Lock className="w-4 h-4 text-blue-600" />
            <span>Data Privacy & Client Confidentiality</span>
          </div>

          <div className="space-y-3 pt-1">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-xs font-semibold text-slate-800 block">
                  Local-Only Data Residency
                </label>
                <p className="text-[11px] text-slate-500">
                  Uploaded contracts and client queries are processed in-memory and stored on-premise.
                </p>
              </div>
              <input
                type="checkbox"
                checked={localCacheOnly}
                onChange={(e) => setLocalCacheOnly(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* System Diagnostics */}
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Server className="w-5 h-5 text-slate-400" />
            <div>
              <div className="text-xs font-bold text-slate-800">
                LegalLens Core Backend: <span className="text-emerald-600">Online & Verified</span>
              </div>
              <p className="text-[11px] text-slate-500">
                Connected to FastAPI backend with SQLite Knowledge Base & Sentence-Transformers Embeddings.
              </p>
            </div>
          </div>

          <button
            onClick={handleSave}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl shadow-xs transition"
          >
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  );
}
