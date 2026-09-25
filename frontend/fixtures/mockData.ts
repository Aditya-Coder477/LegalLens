import { AIResponse, DashboardStats, DocumentDetail, DocumentSummary, SourceOverview } from '../lib/types';

export const mockDashboardStats: DashboardStats = {
  total_documents: 168,
  total_analyses: 32,
  pending_actions: 3,
  recent_documents: [
    {
      document_id: 'SYN-CONT-001',
      title: 'Commercial Employment Agreement (SYN-CONT-001)',
      document_type: 'Contract',
      chunk_count: 12,
      page_count: 8,
      source_authority: 'SYNTHETIC',
      synthetic: true,
      sha256: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
      created_at: '2026-09-25T15:34:00',
    },
    {
      document_id: 'SYN-ACT-001',
      title: 'Digital Data & Intermediary Regulation Act (SYN-ACT-001)',
      document_type: 'Act',
      chunk_count: 76,
      page_count: 24,
      source_authority: 'SYNTHETIC',
      synthetic: true,
      sha256: 'f2f296ad043f7f4a3563fda8f2a6c796964df51d341c06b3622c84dbfc2dc0c0',
      created_at: '2026-09-25T10:04:00',
    },
    {
      document_id: 'USER-DOC-8F32A1',
      title: 'Master Consulting Services Agreement',
      document_type: 'User Document',
      chunk_count: 6,
      page_count: 3,
      source_authority: 'USER_DOCUMENT',
      synthetic: false,
      sha256: 'e892c902bca34821aef459021894081290384910283091823901823901823901',
      created_at: '2026-09-26T01:10:00',
    },
  ],
  recent_activity: [
    {
      event_id: 'act-01',
      event_type: 'AI_ANALYSIS_COMPLETED',
      title: 'Termination clause analyzed',
      description: 'Extracted 30-day notice requirement and verified citations [C1], [C2].',
      timestamp: '2026-09-26T01:25:00',
      document_id: 'SYN-CONT-001',
      badge: 'CLAUSE_ANALYSIS',
    },
    {
      event_id: 'act-02',
      event_type: 'DOCUMENT_UPLOADED',
      title: 'Uploaded Consulting Agreement',
      description: '6 chunks indexed with SHA-256 integrity verification.',
      timestamp: '2026-09-26T01:10:00',
      document_id: 'USER-DOC-8F32A1',
      badge: 'Upload',
    },
  ],
};

export const mockSampleDocument: DocumentDetail = {
  document_id: 'SYN-CONT-001',
  title: 'Commercial Employment Agreement (SYN-CONT-001)',
  document_type: 'Contract',
  chunk_count: 12,
  page_count: 8,
  source_authority: 'SYNTHETIC',
  synthetic: true,
  sha256: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
  created_at: '2026-09-25T15:34:00',
  disclaimer: 'Reference development source — this document is benchmark test data and should not be treated as real law.',
  summary: 'Standard commercial bilateral employment agreement containing provisions on duties, compensation, non-disclosure, 30 days notice for termination, and arbitral dispute resolution.',
  hierarchy: [
    {
      id: 'SYN-CONT-001-SEC-1',
      title: 'Section 1 — Scope of Employment & Duties',
      type: 'section',
      chunk_id: 'SYN-CONT-001-SEC-1',
      page: 1,
      children: [],
    },
    {
      id: 'SYN-CONT-001-SEC-2',
      title: 'Section 2 — Compensation, Emoluments & Taxes',
      type: 'section',
      chunk_id: 'SYN-CONT-001-SEC-2',
      page: 2,
      children: [],
    },
    {
      id: 'SYN-CONT-001-SEC-3',
      title: 'Section 3 — Confidentiality & Proprietary Data',
      type: 'section',
      chunk_id: 'SYN-CONT-001-SEC-3',
      page: 4,
      children: [],
    },
    {
      id: 'SYN-CONT-001-SEC-7',
      title: 'Section 7 — Termination of Employment & Notice',
      type: 'section',
      chunk_id: 'SYN-CONT-001-SEC-7',
      page: 6,
      children: [],
    },
    {
      id: 'SYN-CONT-001-SEC-8',
      title: 'Section 8 — Exceptions to Notice & Summary Dismissal',
      type: 'section',
      chunk_id: 'SYN-CONT-001-SEC-8',
      page: 7,
      children: [],
    },
    {
      id: 'SYN-CONT-001-SEC-10',
      title: 'Section 10 — Return of Property & Equipment',
      type: 'section',
      chunk_id: 'SYN-CONT-001-SEC-10',
      page: 8,
      children: [],
    },
  ],
  raw_text: `COMMERCIAL EMPLOYMENT AGREEMENT

Section 1: Scope of Employment
The Employee shall devote their primary professional energies to fulfilling the obligations set forth in Exhibit A.

Section 2: Compensation
Salary shall be disbursed on or before the final working day of each calendar month via electronic bank transfer.

Section 3: Confidentiality
All technical schematics, client rosters, and financial matrices remain the sole proprietary property of the Employer.

Section 7: Termination & Notice Requirements
(1) Either party may terminate this Agreement without cause by tendering not less than thirty (30) days' written notice to the other party.
(2) In lieu of notice, the Employer may tender thirty (30) days' basic salary.

Section 8: Summary Dismissal & Exceptions
Notwithstanding Section 7, the Employer may terminate immediately without notice upon proven material breach or gross misconduct.

Section 10: Return of Company Property
Within seven (7) days of the effective termination date, Employee must surrender all laptops, encrypted tokens, and proprietary dossiers.`,
};

export const mockSampleAnswer: AIResponse = {
  task_type: 'LEGAL_QA',
  query: 'What happens if I terminate early?',
  direct_answer: 'Under Section 7(1) of the Agreement, either party may terminate by providing not less than thirty (30) days written notice. In lieu of serving notice, the Employer has the option to disburse 30 days basic salary under Section 7(2). However, pursuant to Section 8, summary termination without notice is permitted in cases of gross misconduct or material breach.',
  status: 'VERIFIED',
  confidence: 0.94,
  claims: [
    {
      claim_id: 'C-01',
      text: 'Either party may terminate the agreement by providing at least 30 days written notice.',
      claim_type: 'OBLIGATION',
      evidence_refs: ['SYN-CONT-001-SEC-7'],
      support_status: 'SUPPORTED',
    },
    {
      claim_id: 'C-02',
      text: 'Summary dismissal without notice is reserved for proven material breach or gross misconduct.',
      claim_type: 'LEGAL_PROVISION',
      evidence_refs: ['SYN-CONT-001-SEC-8'],
      support_status: 'SUPPORTED',
    },
  ],
  citations: [
    {
      citation_id: 'C1',
      document_id: 'SYN-CONT-001',
      section: 'Section 7(1)',
      page: 6,
      source_authority: 'SYNTHETIC',
      synthetic: true,
      excerpt: "Either party may terminate this Agreement without cause by tendering not less than thirty (30) days' written notice...",
      sha256: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
      is_valid: true,
      hash_matched: true,
    },
    {
      citation_id: 'C2',
      document_id: 'SYN-CONT-001',
      section: 'Section 8',
      page: 7,
      source_authority: 'SYNTHETIC',
      synthetic: true,
      excerpt: 'Employer may terminate immediately without notice upon proven material breach or gross misconduct.',
      sha256: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
      is_valid: true,
      hash_matched: true,
    },
  ],
  evidence_items: [
    {
      chunk_id: 'SYN-CONT-001-SEC-7',
      document_id: 'SYN-CONT-001',
      section: 'Section 7',
      title: 'Termination & Notice Requirements',
      text: '(1) Either party may terminate this Agreement without cause by tendering not less than thirty (30) days written notice to the other party.\n(2) In lieu of notice, the Employer may tender thirty (30) days basic salary.',
      score: 0.95,
      page_start: 6,
      page_end: 6,
      source_authority: 'SYNTHETIC',
      synthetic: true,
    },
  ],
  contradictions_detected: [],
  synthetic_sources_used: true,
  safety_flags: [],
  next_steps: [
    'Confirm planned effective date of termination in writing',
    'Calculate 30-day notice window or payment-in-lieu calculation',
    'Prepare equipment return dossier under Section 10',
    'Consult an advocate for jurisdiction-specific labor statutory overrides',
  ],
  structured_data: {},
  disclaimer: 'LegalLens provides AI-assisted legal information and document analysis. It is not a substitute for professional legal advice.',
};

export const mockSources: SourceOverview[] = [
  {
    source_id: 'src-acts',
    source_name: 'Reference Parliamentary Acts',
    source_authority: 'SYNTHETIC',
    document_type: 'Act',
    total_documents: 28,
    total_chunks: 1950,
    synthetic: true,
    disclaimer: 'Reference benchmark enactments created for LegalLens development.',
  },
  {
    source_id: 'src-contracts',
    source_name: 'Commercial Agreements & NDAs',
    source_authority: 'SYNTHETIC',
    document_type: 'Contract',
    total_documents: 30,
    total_chunks: 360,
    synthetic: true,
    disclaimer: 'Reference commercial contracts for clause analysis and comparison.',
  },
  {
    source_id: 'src-rules',
    source_name: 'Subordinate Rules & Regulations',
    source_authority: 'SYNTHETIC',
    document_type: 'Rule',
    total_documents: 40,
    total_chunks: 400,
    synthetic: true,
    disclaimer: 'Reference regulatory rulebooks modeled after Indian administrative law.',
  },
  {
    source_id: 'src-notifications',
    source_name: 'Executive Notifications & Circulars',
    source_authority: 'SYNTHETIC',
    document_type: 'Notification',
    total_documents: 30,
    total_chunks: 150,
    synthetic: true,
    disclaimer: 'Reference ministerial notifications for temporal versioning tests.',
  },
  {
    source_id: 'src-judgments',
    source_name: 'Appellate Precedents & Judgments',
    source_authority: 'SYNTHETIC',
    document_type: 'Judgment',
    total_documents: 20,
    total_chunks: 120,
    synthetic: true,
    disclaimer: 'Reference judicial rulings for stare decisis tests.',
  },
  {
    source_id: 'src-user',
    source_name: 'Workspace User Documents',
    source_authority: 'USER_DOCUMENT',
    document_type: 'User Document',
    total_documents: 1,
    total_chunks: 12,
    synthetic: false,
    disclaimer: 'User-provided documents private to this workspace session.',
  },
];
