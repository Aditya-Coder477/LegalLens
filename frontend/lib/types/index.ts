/**
 * frontend/lib/types/index.ts
 * ===========================
 * Strongly-typed domain models for LegalLens.
 * Matches FastAPI backend Pydantic schemas.
 */

export type SourceAuthority =
  | 'OFFICIAL'
  | 'COURT'
  | 'GOVERNMENT'
  | 'LEGAL_AID'
  | 'SECONDARY'
  | 'USER_DOCUMENT'
  | 'SYNTHETIC';

export type ResponseStatus =
  | 'VERIFIED'
  | 'PARTIALLY_SUPPORTED'
  | 'LIMITED_EVIDENCE'
  | 'NO_EVIDENCE'
  | 'CONFLICT'
  | 'BLOCKED'
  | 'ERROR';

export interface LegalHierarchyNode {
  id: string;
  title: string;
  type: 'chapter' | 'section' | 'subsection' | 'clause';
  chunk_id?: string;
  page?: number;
  children: LegalHierarchyNode[];
}

export interface DocumentSummary {
  document_id: string;
  title: string;
  document_type: string;
  chunk_count: number;
  page_count: number;
  source_authority: SourceAuthority | string;
  synthetic: boolean;
  sha256?: string;
  version_id?: string;
  created_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  hierarchy: LegalHierarchyNode[];
  raw_text?: string;
  summary?: string;
  disclaimer: string;
}

export interface Chunk {
  chunk_id: string;
  document_id: string;
  chapter?: string;
  section?: string;
  subsection?: string;
  title?: string;
  text: string;
  page_start?: number;
  page_end?: number;
  source_authority: string;
  synthetic: boolean;
  content_hash?: string;
}

export interface RetrievedEvidence {
  chunk_id: string;
  document_id: string;
  section?: string;
  title?: string;
  text: string;
  score: number;
  page_start?: number;
  page_end?: number;
  source_authority: string;
  synthetic: boolean;
}

export interface Claim {
  claim_id: string;
  text: string;
  claim_type: string;
  evidence_refs: string[];
  support_status: 'SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'UNSUPPORTED' | string;
}

export interface Citation {
  citation_id: string;
  document_id: string;
  section?: string;
  page?: number;
  source_authority: string;
  synthetic: boolean;
  excerpt?: string;
  sha256?: string;
  is_valid: boolean;
  hash_matched: boolean;
}

export interface AIResponse {
  task_type: string;
  query: string;
  direct_answer: string;
  status: ResponseStatus;
  confidence: number;
  claims: Claim[];
  citations: Citation[];
  evidence_items: RetrievedEvidence[];
  contradictions_detected: string[];
  synthetic_sources_used: boolean;
  safety_flags: string[];
  next_steps: string[];
  structured_data: Record<string, any>;
  disclaimer: string;
}

export interface ActivityEvent {
  event_id: string;
  event_type: string;
  title: string;
  description: string;
  timestamp: string;
  document_id?: string;
  badge?: string;
}

export interface DashboardStats {
  total_documents: number;
  total_analyses: number;
  pending_actions: number;
  recent_documents: DocumentSummary[];
  recent_activity: ActivityEvent[];
}

export interface SourceOverview {
  source_id: string;
  source_name: string;
  source_authority: string;
  document_type: string;
  total_documents: number;
  total_chunks: number;
  synthetic: boolean;
  disclaimer: string;
}
