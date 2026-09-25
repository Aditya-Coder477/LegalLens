import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SourceBadge } from '../components/citations/SourceBadge';
import { CitationBadge } from '../components/citations/CitationBadge';
import { SafetyNotice } from '../components/safety/SafetyNotice';
import { SafetyBanner } from '../components/safety/SafetyBanner';
import { EvidencePanel } from '../components/evidence/EvidencePanel';
import { AnswerView } from '../components/analysis/AnswerView';
import { mockSampleAnswer, mockSampleDocument } from '../fixtures/mockData';

describe('LegalLens Frontend Core Components', () => {
  describe('SourceBadge', () => {
    it('renders official gazette badge properly', () => {
      render(<SourceBadge authority="OFFICIAL" synthetic={false} />);
      expect(screen.getByText('Official Gazette')).toBeInTheDocument();
    });

    it('renders reference watermark badge when synthetic=true', () => {
      render(<SourceBadge authority="SYNTHETIC" synthetic={true} />);
      expect(screen.getByText('Reference Corpus')).toBeInTheDocument();
    });

    it('renders court judgment badge', () => {
      render(<SourceBadge authority="COURT" synthetic={false} />);
      expect(screen.getByText('Judicial Ruling')).toBeInTheDocument();
    });

    it('renders user document badge', () => {
      render(<SourceBadge authority="USER_DOCUMENT" synthetic={false} />);
      expect(screen.getByText('User Document')).toBeInTheDocument();
    });
  });

  describe('CitationBadge', () => {
    it('renders clickable citation badge with citation ID', () => {
      const handleClick = vi.fn();
      const citation = mockSampleAnswer.citations[0];
      render(<CitationBadge citation={citation} onClick={handleClick} />);
      const btn = screen.getByRole('button', { name: '[C1]' });
      expect(btn).toBeInTheDocument();
      fireEvent.click(btn);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('SafetyNotice', () => {
    it('renders persistent legal disclaimer notice', () => {
      render(<SafetyNotice />);
      expect(
        screen.getByText(/Legal Information Workspace:/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Reference Development Corpus/i)
      ).toBeInTheDocument();
    });
  });

  describe('SafetyBanner', () => {
    it('renders reference corpus warning banner', () => {
      render(
        <SafetyBanner
          variant="synthetic"
          title="Reference Development Source"
          message="Notice: Development & testing reference legal dataset."
        />
      );
      expect(screen.getByText(/Reference Development Source/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Notice: Development & testing reference legal dataset./i)
      ).toBeInTheDocument();
    });

    it('renders conflict alert banner', () => {
      render(
        <SafetyBanner
          variant="warning"
          title="Statutory Ambiguity Detected"
          message="Conflicting provisions found between central and state enactments."
        />
      );
      expect(screen.getByText('Statutory Ambiguity Detected')).toBeInTheDocument();
      expect(
        screen.getByText(/Conflicting provisions found/i)
      ).toBeInTheDocument();
    });
  });

  describe('EvidencePanel', () => {
    it('renders evidence chunk card with score and section', () => {
      const evidence = mockSampleAnswer.evidence_items[0];
      render(<EvidencePanel evidence={evidence} />);
      expect(screen.getByText(evidence.title!)).toBeInTheDocument();
      expect(screen.getByText(`Sec: ${evidence.section}`)).toBeInTheDocument();
      expect(screen.getByText(/Either party may terminate this agreement/i)).toBeInTheDocument();
    });
  });

  describe('AnswerView', () => {
    it('distinguishes AI explanation from Source evidence and allows opening lawyer handoff', () => {
      const handleHandoff = vi.fn();
      render(
        <AnswerView
          response={mockSampleAnswer}
          onOpenHandoff={handleHandoff}
        />
      );

      // AI explanation section
      expect(screen.getByText(/AI Explanation/i)).toBeInTheDocument();
      expect(screen.getByText(mockSampleAnswer.direct_answer)).toBeInTheDocument();

      // Source Evidence section
      expect(screen.getByText(/Supported By: Source Evidence/i)).toBeInTheDocument();

      // Lawyer handoff button
      const handoffBtn = screen.getByRole('button', { name: /Prepare Lawyer Dossier/i });
      expect(handoffBtn).toBeInTheDocument();
      fireEvent.click(handoffBtn);
      expect(handleHandoff).toHaveBeenCalledTimes(1);
    });
  });

  describe('ThemeToggle', () => {
    it('toggles dark and light mode on click', async () => {
      const { ThemeToggle } = await import('../components/theme/ThemeToggle');
      const { ThemeProvider } = await import('../lib/context/ThemeContext');

      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      const toggleBtn = screen.getByRole('button');
      expect(toggleBtn).toBeInTheDocument();
      expect(toggleBtn).toHaveAttribute('title', 'Switch to dark mode');

      fireEvent.click(toggleBtn);
      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(toggleBtn).toHaveAttribute('title', 'Switch to light mode');

      fireEvent.click(toggleBtn);
      expect(document.documentElement.classList.contains('dark')).toBe(false);
      expect(toggleBtn).toHaveAttribute('title', 'Switch to dark mode');
    });
  });
});
