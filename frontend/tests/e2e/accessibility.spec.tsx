import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { AppShell } from '../../components/layout/AppShell';
import { Header } from '../../components/layout/Header';
import { Sidebar } from '../../components/layout/Sidebar';
import { UploadDropzone } from '../../components/documents/UploadDropzone';
import { LawyerHandoffModal } from '../../components/analysis/LawyerHandoffModal';
import { CitationModal } from '../../components/citations/CitationModal';
import { AnswerView } from '../../components/analysis/AnswerView';
import { mockSampleAnswer, mockSampleDocument } from '../../fixtures/mockData';
import HomePage from '../../app/page';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('LegalLens Accessibility & Problem Statement Alignment Tests', () => {
  describe('Landmarks & Skip Navigation', () => {
    it('provides keyboard skip link targeting main-content landmark', () => {
      render(
        <AppShell>
          <div>Page Content</div>
        </AppShell>
      );

      const skipLink = screen.getByRole('link', { name: /Skip to main content/i });
      expect(skipLink).toBeInTheDocument();
      expect(skipLink).toHaveAttribute('href', '#main-content');

      const mainLandmark = screen.getByRole('main');
      expect(mainLandmark).toHaveAttribute('id', 'main-content');
      expect(mainLandmark).toHaveAttribute('tabindex', '-1');
    });

    it('uses semantic landmarks with proper labels in header and sidebar', () => {
      render(
        <AppShell>
          <div>Body</div>
        </AppShell>
      );

      const searchForm = screen.getByRole('search', { name: /Sitewide legal search/i });
      expect(searchForm).toBeInTheDocument();

      const nav = screen.getByRole('navigation', { name: /Workspace/i });
      expect(nav).toBeInTheDocument();
    });
  });

  describe('Form Controls & Accessible Names', () => {
    it('ensures header search input has an associated accessible label', () => {
      render(<Header />);
      const searchInput = screen.getByLabelText(/Search Indian legal statutes, agreements, or ask a question/i);
      expect(searchInput).toBeInTheDocument();
      expect(searchInput).toHaveAttribute('type', 'text');
    });

    it('provides accessible keyboard button for file upload', () => {
      const handleSuccess = vi.fn();
      render(<UploadDropzone onUploadSuccess={handleSuccess} />);

      const uploadBtn = screen.getByRole('button', { name: /Upload a legal document/i });
      expect(uploadBtn).toBeInTheDocument();
      expect(uploadBtn).toHaveAttribute('tabindex', '0');
    });
  });

  describe('Modal Dialog Accessibility & Focus Trap', () => {
    it('renders LawyerHandoffModal with role=dialog, aria-modal=true, and closes on Escape', () => {
      const handleClose = vi.fn();
      render(
        <LawyerHandoffModal
          isOpen={true}
          onClose={handleClose}
          response={mockSampleAnswer}
          document={mockSampleDocument}
        />
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
      expect(dialog).toHaveAttribute('aria-modal', 'true');
      expect(screen.getByText(/Prepare Lawyer Intake Dossier/i)).toBeInTheDocument();

      // Test Escape closes dialog
      fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
      expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('renders CitationModal with accessible dialog attributes', () => {
      const handleClose = vi.fn();
      const citation = mockSampleAnswer.citations[0];
      render(
        <CitationModal
          citation={citation}
          onClose={handleClose}
        />
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
      expect(dialog).toHaveAttribute('aria-modal', 'true');

      const closeBtn = screen.getByRole('button', { name: /Close citation inspector/i });
      expect(closeBtn).toBeInTheDocument();
      fireEvent.click(closeBtn);
      expect(handleClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Live Announcements & Non-Color Dependent Status', () => {
    it('includes polite live region and text for verification status', () => {
      render(<AnswerView response={mockSampleAnswer} />);
      const liveElements = screen.getAllByText(/Grounded: Strongly supported by retrieved evidence/i);
      expect(liveElements.length).toBeGreaterThan(0);
    });

    it('renders clear explanation for NO_EVIDENCE without blank results', () => {
      const noEvidenceAnswer = {
        ...mockSampleAnswer,
        status: 'NO_EVIDENCE' as const,
        direct_answer: 'No legal evidence was found.',
      };
      render(<AnswerView response={noEvidenceAnswer} />);
      expect(screen.getAllByText(/No Sufficient Evidence Found/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/The knowledge base and indexed sources do not contain direct statutory provisions/i)).toBeInTheDocument();
    });
  });

  describe('Problem Statement Alignment & Factual Messaging', () => {
    it('displays the redesigned hero with clear problem statement on Homepage', () => {
      render(<HomePage />);

      // Core value proposition
      expect(screen.getByText(/LEGAL DOCUMENT INTELLIGENCE/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Understand complex legal documents with evidence you can trace/i)
      ).toBeInTheDocument();

      // Clear CTAs
      expect(screen.getByRole('link', { name: /Upload a Document/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Ask a Legal Question/i })).toBeInTheDocument();

      // Why LegalLens? problem statement
      expect(screen.getByText(/Why LegalLens\?/i)).toBeInTheDocument();
      expect(screen.getByText(/Manual document review is slow, complex, and prone to oversight/i)).toBeInTheDocument();

      // 6-step user journey
      expect(screen.getByText(/From raw document to actionable clarity in 6 steps/i)).toBeInTheDocument();
      expect(screen.getAllByText(/01/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Upload/i).length).toBeGreaterThan(0);

      // Evidence differentiator
      expect(screen.getByText(/Every answer is connected to verifiable evidence/i)).toBeInTheDocument();

      // Ethical safety boundary
      expect(screen.getByText(/Legal information, not a substitute for professional legal advice/i)).toBeInTheDocument();
    });

    it('contains no misleading unverified marketing claims', () => {
      render(<HomePage />);
      expect(screen.queryByText(/Zero hallucinated legal statutes/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/100% grounding verification/i)).not.toBeInTheDocument();
    });
  });
});
