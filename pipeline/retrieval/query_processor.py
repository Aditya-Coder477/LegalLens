"""
pipeline/retrieval/query_processor.py
=====================================
Deterministic query normalization, legal reference extraction, and query type classification.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

from .models import QueryType


# ──────────────────────────────────────────────
# Legal regex patterns
# ──────────────────────────────────────────────

RE_SECTION = re.compile(r"\b(?:Section|Sec\.?|S\.)\s*(\d+[A-Z]?)(?:\((\d+)\))?(?:\(([a-z])\))?", re.IGNORECASE)
RE_RULE = re.compile(r"\b(?:Rule|R\.)\s*(\d+[A-Z]?)(?:\((\d+)\))?", re.IGNORECASE)
RE_ARTICLE = re.compile(r"\b(?:Article|Art\.?)\s*(\d+[A-Z]?)", re.IGNORECASE)
RE_CLAUSE = re.compile(r"\b(?:Clause|Cl\.?)\s*(\d+[A-Z]?)", re.IGNORECASE)
RE_ACT_ID = re.compile(r"\b(SYN-ACT-\d{3}(?:-v\d+)?)\b", re.IGNORECASE)
RE_RULE_ID = re.compile(r"\b(SYN-RULE-\d{3})\b", re.IGNORECASE)
RE_JUDG_ID = re.compile(r"\b(SYN-JUDG-\d{3})\b", re.IGNORECASE)
RE_CONT_ID = re.compile(r"\b(SYN-CONT-\d{3})\b", re.IGNORECASE)
RE_QUOTED = re.compile(r'["\']([^"\']{2,80})["\']')


class QueryProcessor:
    """
    Processes and normalizes legal search queries and detects query characteristics.
    """

    def normalize(self, query: str) -> str:
        """
        Clean whitespace and normalize Unicode while preserving critical legal identifiers.
        """
        if not query:
            return ""

        # Unicode NFKC normalization
        norm = unicodedata.normalize("NFKC", query)

        # Collapse whitespace
        norm = re.sub(r"\s+", " ", norm).strip()
        return norm

    def expand_for_retrieval(self, query: str) -> str:
        """
        Expand query with extracted statutory entities and synonyms for expanded retrieval.
        """
        if not query:
            return ""
        entities = self.extract_legal_entities(query)
        tokens = [query]
        for sec in entities.get("sections", []):
            tokens.append(f"Section {sec}")
        for act in entities.get("enactments", []):
            tokens.append(act)
        return " ".join(tokens)

    def extract_legal_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Extract exact legal provisions, enactment references, and quoted terms.
        """
        results: Dict[str, List[str]] = {
            "sections": [],
            "rules": [],
            "articles": [],
            "clauses": [],
            "enactments": [],
            "quoted_terms": [],
        }

        # Sections
        for m in RE_SECTION.finditer(query):
            sec = m.group(1)
            if m.group(2):
                sec += f"({m.group(2)})"
            if m.group(3):
                sec += f"({m.group(3)})"
            results["sections"].append(sec)

        # Rules
        for m in RE_RULE.finditer(query):
            r = m.group(1)
            if m.group(2):
                r += f"({m.group(2)})"
            results["rules"].append(r)

        # Articles
        for m in RE_ARTICLE.finditer(query):
            results["articles"].append(m.group(1))

        # Clauses
        for m in RE_CLAUSE.finditer(query):
            results["clauses"].append(m.group(1))

        # Enactment IDs
        for pattern in (RE_ACT_ID, RE_RULE_ID, RE_JUDG_ID, RE_CONT_ID):
            for m in pattern.finditer(query):
                results["enactments"].append(m.group(1).upper())

        # Quoted terms
        for m in RE_QUOTED.finditer(query):
            results["quoted_terms"].append(m.group(1).strip())

        return results

    def detect_query_type(self, query: str) -> QueryType:
        """
        Determine the legal intent / type of the query using deterministic pattern matching.
        """
        q_lower = query.lower()

        # 1. Penalty / Offence query
        if re.search(r"\b(?:penalty|penalties|fine|fines|punishment|imprisonment|offence|liable to pay|late fee)\b", q_lower):
            return QueryType.PENALTY

        # 2. Right / Remedy query
        if re.search(r"\b(?:right to|rights|entitled to|eligible for|remedy|remedies|redressal|claim refund)\b", q_lower):
            return QueryType.RIGHT

        # 3. Obligation query
        if re.search(r"\b(?:obligation|obligations|mandatory|statutory duty|must|shall|compliance requirement|duty)\b", q_lower):
            return QueryType.OBLIGATION

        # 4. Cross reference query
        if re.search(r"\b(?:refer to|referred in|referred to|cross-reference|parent act|under section|which provision)\b", q_lower):
            return QueryType.CROSS_REFERENCE

        # 5. Definition query
        if (
            re.search(r"\b(?:define|meaning of|definition of)\b", q_lower)
            or re.search(r"\bwhat is (?:a|an|the term)\b", q_lower)
            or re.search(r'["\'][^"\']+["\']\s*(?:means|defined as)', q_lower)
        ):
            return QueryType.DEFINITION

        # 6. Section / Rule lookup
        if (
            re.search(r"\b(?:section|rule|article|clause)\s+\d+", q_lower)
            and not re.search(r"\b(?:how to)\b", q_lower)
        ):
            return QueryType.SECTION_LOOKUP

        # Contract clause query
        if re.search(r"\b(?:contract|agreement|indemnity|termination for convenience|force majeure|party a|party b|master services)\b", q_lower):
            return QueryType.CONTRACT_CLAUSE

        # Judgment query
        if re.search(r"\b(?:court|bench|judgment|ruling|held that|petitioner|respondent|writ petition|coram)\b", q_lower):
            return QueryType.JUDGMENT

        # Cross reference query
        if re.search(r"\b(?:refer to|referred in|cross-reference|parent act|under section)\b", q_lower):
            return QueryType.CROSS_REFERENCE

        # Comparison query
        if re.search(r"\b(?:compare|difference between|versus|distinction between)\b", q_lower):
            return QueryType.COMPARISON

        # Procedure query
        if re.search(r"\b(?:procedure|process|how to file|steps to|timeline for|within how many days)\b", q_lower):
            return QueryType.PROCEDURE

        return QueryType.GENERAL
