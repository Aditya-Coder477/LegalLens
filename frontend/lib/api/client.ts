/**
 * frontend/lib/api/client.ts
 * ==========================
 * Typed API Client for LegalLens REST backend.
 * Provides resilient fetch operations with fallback to mock fixtures.
 */

import {
  AIResponse,
  Chunk,
  DashboardStats,
  DocumentDetail,
  DocumentSummary,
  RetrievedEvidence,
  SourceOverview,
  ActivityEvent,
} from '../types';
import {
  mockDashboardStats,
  mockSampleAnswer,
  mockSampleDocument,
  mockSources,
} from '../../fixtures/mockData';

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
const IS_MOCK_MODE = process.env.NEXT_PUBLIC_API_MODE === 'mock';

// In-memory cache for idempotent read queries to eliminate duplicate network calls
interface CacheEntry<T> {
  data: T;
  timestamp: number;
}
const requestCache = new Map<string, CacheEntry<any>>();
const pendingRequests = new Map<string, Promise<any>>();
const CACHE_TTL_MS = 30000; // 30 seconds

async function safeFetch<T>(
  endpoint: string,
  options?: RequestInit,
  fallback?: T,
  forceRefresh: boolean = false
): Promise<T> {
  if (IS_MOCK_MODE && fallback !== undefined) {
    return fallback;
  }

  const isGet = !options?.method || options.method.toUpperCase() === 'GET';
  const cacheKey = `${endpoint}`;

  // 1. Check in-memory cache for GET requests
  if (isGet && !forceRefresh) {
    const cached = requestCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      return cached.data as T;
    }
  }

  // 2. Request deduplication for simultaneous in-flight GET requests
  if (isGet && pendingRequests.has(cacheKey) && !forceRefresh) {
    return pendingRequests.get(cacheKey) as Promise<T>;
  }

  const fetchPromise = (async () => {
    try {
      const res = await fetch(`${BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...(options?.headers || {}),
        },
        ...options,
      });

      if (!res.ok) {
        throw new Error(`API error ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();

      // Store successful GET responses in cache
      if (isGet) {
        requestCache.set(cacheKey, { data, timestamp: Date.now() });
      }

      return data as T;
    } catch (err) {
      if (fallback !== undefined) {
        console.warn(`[LegalLens API Client] Request failed for ${endpoint}, using fallback.`, err);
        return fallback;
      }
      throw err;
    } finally {
      if (isGet) {
        pendingRequests.delete(cacheKey);
      }
    }
  })();

  if (isGet) {
    pendingRequests.set(cacheKey, fetchPromise);
  }

  return fetchPromise;
}

export const LegalLensAPI = {
  invalidateCache(pattern?: string) {
    if (!pattern) {
      requestCache.clear();
      return;
    }
    requestCache.forEach((_, key) => {
      if (key.includes(pattern)) {
        requestCache.delete(key);
      }
    });
  },

  async getDashboard(forceRefresh = false): Promise<DashboardStats> {
    return safeFetch<DashboardStats>('/api/v1/dashboard', { method: 'GET' }, mockDashboardStats, forceRefresh);
  },

  async getDocuments(forceRefresh = false): Promise<DocumentSummary[]> {
    return safeFetch<DocumentSummary[]>('/api/v1/documents', { method: 'GET' }, mockDashboardStats.recent_documents, forceRefresh);
  },

  async getDocument(documentId: string, forceRefresh = false): Promise<DocumentDetail> {
    return safeFetch<DocumentDetail>(
      `/api/v1/documents/${documentId}`,
      { method: 'GET' },
      { ...mockSampleDocument, document_id: documentId },
      forceRefresh
    );
  },

  async getDocumentChunks(documentId: string, forceRefresh = false): Promise<Chunk[]> {
    return safeFetch<Chunk[]>(`/api/v1/documents/${documentId}/chunks`, { method: 'GET' }, [], forceRefresh);
  },

  async uploadFile(file: File, title?: string, documentType: string = 'Contract'): Promise<DocumentSummary> {
    this.invalidateCache();
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    formData.append('document_type', documentType);

    try {
      const res = await fetch(`${BASE_URL}/api/v1/documents/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
      return await res.json();
    } catch (err) {
      console.warn('[LegalLens API Client] File upload fallback', err);
      return {
        document_id: `USER-DOC-${Date.now().toString().slice(-6)}`,
        title: title || file.name.replace(/\.[^/.]+$/, ''),
        document_type: documentType,
        chunk_count: 8,
        page_count: 4,
        source_authority: 'USER_DOCUMENT',
        synthetic: false,
        created_at: new Date().toISOString(),
      };
    }
  },

  async uploadDocument(title: string, documentType: string, textContent: string): Promise<DocumentSummary> {
    this.invalidateCache();
    return safeFetch<DocumentSummary>(
      '/api/v1/documents/upload-json',
      {
        method: 'POST',
        body: JSON.stringify({
          title,
          document_type: documentType,
          text_content: textContent,
          source_authority: 'USER_DOCUMENT',
          synthetic: false,
        }),
      },
      {
        document_id: `USER-DOC-${Date.now().toString().slice(-6)}`,
        title,
        document_type: documentType,
        chunk_count: 5,
        page_count: 2,
        source_authority: 'USER_DOCUMENT',
        synthetic: false,
        created_at: new Date().toISOString(),
      }
    );
  },

  async retrieveEvidence(query: string, documentId?: string, topK: number = 5): Promise<RetrievedEvidence[]> {
    const data = await safeFetch<{ results: RetrievedEvidence[] }>(
      '/api/v1/retrieve',
      {
        method: 'POST',
        body: JSON.stringify({ query, document_id: documentId, top_k: topK }),
      },
      { results: mockSampleAnswer.evidence_items }
    );
    return data.results;
  },

  async askLegalLens(query: string, documentId?: string, userFacts?: any[], topK: number = 5): Promise<AIResponse> {
    return safeFetch<AIResponse>(
      '/api/v1/ai/answer',
      {
        method: 'POST',
        body: JSON.stringify({ query, document_id: documentId, user_facts: userFacts, top_k: topK }),
      },
      { ...mockSampleAnswer, query }
    );
  },

  async summarizeDocument(documentId?: string, documentText?: string, query?: string): Promise<AIResponse> {
    return safeFetch<AIResponse>(
      '/api/v1/ai/summarize',
      {
        method: 'POST',
        body: JSON.stringify({ document_id: documentId, document_text: documentText, query: query || 'Summarize this document' }),
      },
      {
        ...mockSampleAnswer,
        task_type: 'SUMMARY',
        direct_answer: 'Executive Summary: This document regulates commercial obligations, notice requirements, confidentiality, and remedies for breach.',
      }
    );
  },

  async simplifyText(text: string, documentId?: string): Promise<AIResponse> {
    return safeFetch<AIResponse>(
      '/api/v1/ai/simplify',
      {
        method: 'POST',
        body: JSON.stringify({ text, document_id: documentId }),
      },
      {
        ...mockSampleAnswer,
        task_type: 'SIMPLIFY',
        direct_answer: 'In plain language: Both parties must give 30 days notice before ending the contract, or pay 1 month salary instead.',
      }
    );
  },

  async analyzeClause(clauseText: string, documentId?: string): Promise<AIResponse> {
    return safeFetch<AIResponse>(
      '/api/v1/ai/analyze-clause',
      {
        method: 'POST',
        body: JSON.stringify({ clause_text: clauseText, document_id: documentId }),
      },
      {
        ...mockSampleAnswer,
        task_type: 'CLAUSE_ANALYSIS',
        direct_answer: 'Clause Analysis: This clause establishes bilateral termination rights with a 30-day notice requirement.',
      }
    );
  },

  async compareDocuments(docAId?: string, docBId?: string, docAText?: string, docBText?: string): Promise<AIResponse> {
    return safeFetch<AIResponse>(
      '/api/v1/ai/compare',
      {
        method: 'POST',
        body: JSON.stringify({ doc_a_id: docAId, doc_b_id: docBId, doc_a_text: docAText, doc_b_text: docBText }),
      },
      {
        ...mockSampleAnswer,
        task_type: 'COMPARE_DOCUMENTS',
        direct_answer: 'Document Comparison: Version 1 stipulates 30 days notice whereas Version 2 increases notice to 60 days.',
      }
    );
  },

  async extractObligations(documentId?: string, documentText?: string): Promise<AIResponse> {
    return safeFetch<AIResponse>(
      '/api/v1/ai/obligations',
      {
        method: 'POST',
        body: JSON.stringify({ document_id: documentId, document_text: documentText }),
      },
      {
        ...mockSampleAnswer,
        task_type: 'EXTRACT_OBLIGATIONS',
        direct_answer: 'Extracted mandatory obligations for Employee and Employer.',
      }
    );
  },

  async extractDeadlines(documentId?: string, documentText?: string): Promise<AIResponse> {
    return safeFetch<AIResponse>(
      '/api/v1/ai/deadlines',
      {
        method: 'POST',
        body: JSON.stringify({ document_id: documentId, document_text: documentText }),
      },
      {
        ...mockSampleAnswer,
        task_type: 'EXTRACT_DEADLINES',
        direct_answer: 'Extracted deadlines: 30 days for termination notice, 7 days for return of equipment.',
      }
    );
  },

  async getSources(forceRefresh = false): Promise<SourceOverview[]> {
    return safeFetch<SourceOverview[]>('/api/v1/sources', { method: 'GET' }, mockSources, forceRefresh);
  },

  async getActivity(forceRefresh = false): Promise<ActivityEvent[]> {
    return safeFetch<ActivityEvent[]>('/api/v1/activity', { method: 'GET' }, mockDashboardStats.recent_activity, forceRefresh);
  },
};
