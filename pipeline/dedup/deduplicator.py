"""
pipeline/dedup/deduplicator.py
================================
Deduplication engine implementing four complementary strategies:

1. URL deduplication     — normalised canonical URL comparison
2. SHA-256 deduplication — exact binary file match
3. Title+year+act-no     — structured metadata match for different-URL same-document
4. Normalized title similarity — Levenshtein ratio ≥ threshold for title-only variants

Output: duplicate_report.json in legal-data/datasets/
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from pipeline.core.logger import get_logger

log = get_logger("deduplicator")


# ──────────────────────────────────────────────
# URL normalisation
# ──────────────────────────────────────────────

def normalise_url(url: str) -> str:
    """
    Normalise a URL for deduplication purposes:
    - Lowercase scheme + netloc
    - Strip fragment
    - Sort query parameters
    - Remove trailing slash from path
    - Strip utm_* and other tracking params
    """
    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "ref", "referrer", "_ga",
    }
    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/").lower()
        params = {
            k: v for k, v in parse_qs(parsed.query).items()
            if k not in TRACKING_PARAMS
        }
        query = urlencode(sorted(params.items()))
        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return url.strip().lower()


# ──────────────────────────────────────────────
# Title normalisation
# ──────────────────────────────────────────────

def normalise_title(title: str) -> str:
    """Normalise a document title for fuzzy comparison."""
    # Unicode normalisation
    title = unicodedata.normalize("NFKC", title)
    title = title.lower()
    # Remove "the", common legal words that vary across versions
    title = re.sub(r"\b(the|an|a|of|and|in|to|for|with|act|law)\b", " ", title)
    # Remove 4-digit years (e.g. 1860, 2023)
    title = re.sub(r"\b\d{4}\b", " ", title)
    # Collapse whitespace
    title = re.sub(r"\s+", " ", title).strip()
    # Remove punctuation except digits
    title = re.sub(r"[^\w\d\s]", "", title)
    return title


def title_similarity(t1: str, t2: str) -> float:
    """
    Return Levenshtein similarity ratio between two normalised titles.
    Uses rapidfuzz for speed; falls back to difflib if not installed.
    """
    n1 = normalise_title(t1)
    n2 = normalise_title(t2)
    if n1 == n2:
        return 1.0
    try:
        from rapidfuzz.distance import Levenshtein
        max_len = max(len(n1), len(n2), 1)
        dist = Levenshtein.distance(n1, n2)
        return 1.0 - dist / max_len
    except ImportError:
        from difflib import SequenceMatcher
        return SequenceMatcher(None, n1, n2).ratio()


# ──────────────────────────────────────────────
# Deduplicator
# ──────────────────────────────────────────────

class DuplicateGroup:
    """Represents a set of documents that are duplicates of each other."""
    def __init__(self, primary_id: str, primary_url: str, primary_title: str):
        self.primary_id = primary_id
        self.primary_url = primary_url
        self.primary_title = primary_title
        self.duplicates: list[dict] = []
        self.reason: str = ""


class Deduplicator:
    """
    Runs all four deduplication strategies on the document catalogue.

    Usage:
        dedup = Deduplicator(similarity_threshold=0.92)
        groups = dedup.run(documents)   # documents = list of dicts from catalogue
        dedup.save_report(groups, output_dir="legal-data/datasets")
    """

    def __init__(self, similarity_threshold: float = 0.92) -> None:
        self._threshold = similarity_threshold

    def run(self, documents: list[dict]) -> list[DuplicateGroup]:
        """
        Detect duplicates across all four strategies.

        Args:
            documents: List of document dicts from Catalogue.documents.

        Returns:
            List of DuplicateGroup objects.
        """
        groups: list[DuplicateGroup] = []

        # 1. URL deduplication
        groups.extend(self._url_dedup(documents))

        # 2. SHA-256 deduplication
        groups.extend(self._sha256_dedup(documents))

        # 3. Title + year + act-number deduplication
        groups.extend(self._metadata_dedup(documents))

        # 4. Title similarity
        groups.extend(self._title_similarity_dedup(documents))

        log.info(
            "Deduplication complete",
            duplicate_groups=len(groups),
            duplicate_pairs=sum(len(g.duplicates) for g in groups),
        )
        return groups

    def _url_dedup(self, docs: list[dict]) -> list[DuplicateGroup]:
        seen: dict[str, dict] = {}
        groups: list[DuplicateGroup] = []
        for doc in docs:
            url = doc.get("official_url", "")
            if not url:
                continue
            norm = normalise_url(url)
            if norm in seen:
                primary = seen[norm]
                grp = DuplicateGroup(
                    primary_id=primary.get("source_id", ""),
                    primary_url=url,
                    primary_title=primary.get("title", ""),
                )
                grp.reason = "url_duplicate"
                grp.duplicates.append({"source_id": doc.get("source_id"), "url": url, "reason": "url"})
                groups.append(grp)
            else:
                seen[norm] = doc
        return groups

    def _sha256_dedup(self, docs: list[dict]) -> list[DuplicateGroup]:
        seen: dict[str, dict] = {}
        groups: list[DuplicateGroup] = []
        for doc in docs:
            sha = (doc.get("sha256") or "").strip().lower()
            if not sha or len(sha) != 64:
                continue
            if sha in seen:
                primary = seen[sha]
                grp = DuplicateGroup(
                    primary_id=primary.get("source_id", ""),
                    primary_url=primary.get("official_url", ""),
                    primary_title=primary.get("title", ""),
                )
                grp.reason = "sha256_duplicate"
                grp.duplicates.append({
                    "source_id": doc.get("source_id"),
                    "url": doc.get("official_url"),
                    "reason": "sha256",
                    "sha256": sha,
                })
                groups.append(grp)
            else:
                seen[sha] = doc
        return groups

    def _metadata_dedup(self, docs: list[dict]) -> list[DuplicateGroup]:
        """Deduplicate by (act_number, act_year, source_name) tuple."""
        seen: dict[tuple, dict] = {}
        groups: list[DuplicateGroup] = []
        for doc in docs:
            act_num = (doc.get("act_number") or "").strip()
            act_year = (doc.get("act_year") or "").strip()
            source = (doc.get("source_name") or "").strip()
            if not act_num or not act_year:
                continue
            key = (act_num.lower(), act_year, source.lower())
            if key in seen:
                primary = seen[key]
                grp = DuplicateGroup(
                    primary_id=primary.get("source_id", ""),
                    primary_url=primary.get("official_url", ""),
                    primary_title=primary.get("title", ""),
                )
                grp.reason = "metadata_duplicate"
                grp.duplicates.append({
                    "source_id": doc.get("source_id"),
                    "url": doc.get("official_url"),
                    "reason": "act_number+year",
                })
                groups.append(grp)
            else:
                seen[key] = doc
        return groups

    def _title_similarity_dedup(self, docs: list[dict]) -> list[DuplicateGroup]:
        """O(n²) title similarity scan — skipped for large collections (> 10,000 docs)."""
        if len(docs) > 10000:
            log.warning(
                "Title similarity dedup skipped (> 10,000 docs)",
                note="Run on smaller batches or use a vector index for large corpora",
            )
            return []

        groups: list[DuplicateGroup] = []
        visited: set[int] = set()

        for i, doc_a in enumerate(docs):
            if i in visited:
                continue
            title_a = doc_a.get("title", "")
            year_a = doc_a.get("act_year", "")
            for j, doc_b in enumerate(docs):
                if i >= j or j in visited:
                    continue
                title_b = doc_b.get("title", "")
                year_b = doc_b.get("act_year", "")
                # Only compare same year to reduce false positives
                if year_a and year_b and year_a != year_b:
                    continue
                sim = title_similarity(title_a, title_b)
                if sim >= self._threshold:
                    grp = DuplicateGroup(
                        primary_id=doc_a.get("source_id", ""),
                        primary_url=doc_a.get("official_url", ""),
                        primary_title=title_a,
                    )
                    grp.reason = "title_similarity"
                    grp.duplicates.append({
                        "source_id": doc_b.get("source_id"),
                        "url": doc_b.get("official_url"),
                        "reason": f"title_similarity={sim:.3f}",
                    })
                    groups.append(grp)
                    visited.add(j)

        return groups

    def save_report(
        self,
        groups: list[DuplicateGroup],
        output_dir: str = "legal-data/datasets",
    ) -> Path:
        """Save duplicate report to JSON."""
        out = Path(output_dir) / "duplicate_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "total_duplicate_groups": len(groups),
            "total_duplicate_pairs": sum(len(g.duplicates) for g in groups),
            "groups": [
                {
                    "primary_id": g.primary_id,
                    "primary_url": g.primary_url,
                    "primary_title": g.primary_title,
                    "reason": g.reason,
                    "duplicates": g.duplicates,
                }
                for g in groups
            ],
        }
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("Duplicate report saved", path=str(out))
        return out
