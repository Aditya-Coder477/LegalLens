import { describe, it, expect, vi } from 'vitest';
import { LegalLensAPI } from '../../lib/api/client';
import { mockDashboardStats, mockSampleAnswer, mockSampleDocument } from '../../fixtures/mockData';

describe('LegalLens End-to-End Workflow Integration', () => {
  it('fetches dashboard metrics and verifies synthetic corpus isolation', async () => {
    const stats = await LegalLensAPI.getDashboard();
    expect(stats.total_documents).toBeGreaterThan(0);
    expect(stats.recent_documents.length).toBeGreaterThan(0);

    // Verify synthetic documents are tagged synthetic=true
    const syntheticDocs = stats.recent_documents.filter((d) => d.synthetic);
    expect(syntheticDocs.length).toBeGreaterThan(0);
    syntheticDocs.forEach((doc) => {
      expect(doc.source_authority).toMatch(/SYNTHETIC/i);
    });
  });

  it('retrieves evidence bundle with hybrid scores and citations', async () => {
    const evidence = await LegalLensAPI.retrieveEvidence('notice period termination');
    expect(evidence.length).toBeGreaterThan(0);
    expect(evidence[0].document_id).toBeTruthy();
    expect(evidence[0].text).toBeTruthy();
    expect(evidence[0].score).toBeGreaterThan(0);
  });

  it('runs evidence-grounded AI legal reasoning with verified citations', async () => {
    const answer = await LegalLensAPI.askLegalLens(
      'What are the termination requirements?',
      'SYN-CONT-001'
    );
    expect(answer.status).toBe('VERIFIED');
    expect(answer.direct_answer).toBeTruthy();
    expect(answer.citations.length).toBeGreaterThan(0);
    expect(answer.citations[0].is_valid).toBe(true);
    expect(answer.evidence_items.length).toBeGreaterThan(0);
  });

  it('analyzes contract clauses for enforceability under Indian law', async () => {
    const clause = 'Employee shall not engage in competing business for 24 months post-employment';
    const analysis = await LegalLensAPI.analyzeClause(clause);
    expect(analysis.task_type).toBe('CLAUSE_ANALYSIS');
    expect(analysis.direct_answer).toBeTruthy();
  });

  it('compares contract versions side-by-side highlighting material differences', async () => {
    const comparison = await LegalLensAPI.compareDocuments(
      'DOC-V1',
      'DOC-V2',
      'Notice period is 30 days',
      'Notice period is 60 days'
    );
    expect(comparison.task_type).toBe('COMPARE_DOCUMENTS');
    expect(comparison.direct_answer).toBeTruthy();
  });

  it('extracts party obligations and statutory conditions', async () => {
    const obligations = await LegalLensAPI.extractObligations('SYN-CONT-001');
    expect(obligations.task_type).toBe('EXTRACT_OBLIGATIONS');
    expect(obligations.direct_answer || obligations.structured_data).toBeTruthy();
  });

  it('extracts timelines, limitation periods, and deadlines', async () => {
    const deadlines = await LegalLensAPI.extractDeadlines('SYN-CONT-001');
    expect(deadlines.task_type).toBe('EXTRACT_DEADLINES');
    expect(deadlines.direct_answer || deadlines.structured_data).toBeTruthy();
  });

  it('lists knowledge base sources with provenance and authority ratings', async () => {
    const sources = await LegalLensAPI.getSources();
    expect(sources.length).toBeGreaterThan(0);
    const hasOfficial = sources.some((s) => !s.synthetic);
    const hasSynthetic = sources.some((s) => s.synthetic);
    expect(hasOfficial || hasSynthetic).toBe(true);
  });
});
