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

async function safeFetch<T>(endpoint: string, options?: RequestInit, fallback?: T): Promise<T> {
  if (IS_MOCK_MODE && fallback !== undefined) {
    return fallback;
  }

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

    return await res.json();
  } catch (err) {
    if (fallback !== undefined) {
      console.warn(`[LegalLens API Client] Request failed for ${endpoint}, using fallback.`, err);
      return fallback;
    }
    throw err;
  }
}

export const LegalLensAPI = {
  async getDashboard(): Promise<DashboardStats> {
    return safeFetch<DashboardStats>('/api/v1/dashboard', { method: 'GET' }, mockDashboardStats);
  },

  async getDocuments(): Promise<DocumentSummary[]> {
    return safeFetch<DocumentSummary[]>('/api/v1/documents', { method: 'GET' }, mockDashboardStats.recent_documents);
  },

  async getDocument(documentId: string): Promise<DocumentDetail> {
    return safeFetch<DocumentDetail>(
      `/api/v1/documents/${documentId}`,
      { method: 'GET' },
      { ...mockSampleDocument, document_id: documentId }
    );
  },

  async getDocumentChunks(documentId: string): Promise<Chunk[]> {
    return safeFetch<Chunk[]>(`/api/v1/documents/${documentId}/chunks`, { method: 'GET' }, []);
  },

  async uploadFile(file: File, title?: string, documentType: string = 'Contract'): Promise<DocumentSummary> {
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

  async getSources(): Promise<SourceOverview[]> {
    return safeFetch<SourceOverview[]>('/api/v1/sources', { method: 'GET' }, mockSources);
  },

  async getActivity(): Promise<ActivityEvent[]> {
    return safeFetch<ActivityEvent[]>('/api/v1/activity', { method: 'GET' }, mockDashboardStats.recent_activity);
  },
};
