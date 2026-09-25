"""
pipeline/legal_ai/task_classifier.py
====================================
Deterministic rule-based task classifier for routing requests to specialized legal reasoning pipelines.
"""

from __future__ import annotations

import re
from typing import Optional

from .models import TaskType


class TaskClassifier:
    """
    Classifies user intent into a specific TaskType without extra LLM overhead.
    """

    def classify(self, text: str, has_doc_a: bool = False, has_doc_b: bool = False) -> TaskType:
        if not text:
            return TaskType.LEGAL_QA

        t_lower = text.lower()

        # Multi-document comparison
        if has_doc_a and has_doc_b:
            return TaskType.COMPARE_DOCUMENTS
        if re.search(r"\b(?:compare|comparison between|diff between|differences between)\b", t_lower):
            return TaskType.COMPARE_DOCUMENTS

        # Summarization
        if re.search(r"\b(?:summarize|summary of|give an overview of|executive summary)\b", t_lower):
            return TaskType.SUMMARY

        # Simplification
        if re.search(r"\b(?:simplify|plain language|simple terms|explain in simple|plain english)\b", t_lower):
            return TaskType.SIMPLIFY

        # Clause / provision analysis
        if re.search(r"\b(?:analyze (?:.*?\b)?clause|analyze (?:.*?\b)?provision|clause analysis|provision analysis|examine (?:.*?\b)?clause|review (?:.*?\b)?clause|redline)\b", t_lower):
            return TaskType.CLAUSE_ANALYSIS

        # Deadlines
        if re.search(r"\b(?:deadlines|time limit|due date|expiration|timeline for submission|notice period)\b", t_lower):
            return TaskType.EXTRACT_DEADLINES

        # Obligations
        if re.search(r"\b(?:obligations|what must the|duties of|mandatory requirements|compliance obligations)\b", t_lower):
            return TaskType.EXTRACT_OBLIGATIONS

        # Rights and duties
        if re.search(r"\b(?:rights and duties|what rights|entitled to|prohibitions|permissions)\b", t_lower):
            return TaskType.EXTRACT_RIGHTS_DUTIES

        # Issue identification
        if re.search(r"\b(?:identify issues|legal risks|legal issues|find risks|potential liabilities|contract risks)\b", t_lower):
            return TaskType.IDENTIFY_ISSUES

        # Next steps
        if re.search(r"\b(?:next steps|recommended actions|what should i do next|procedural options)\b", t_lower):
            return TaskType.NEXT_STEPS

        # Checklist
        if re.search(r"\b(?:checklist|compliance checklist|audit checklist|action items)\b", t_lower):
            return TaskType.CHECKLIST

        # Default to Grounded Legal Q&A
        return TaskType.LEGAL_QA
