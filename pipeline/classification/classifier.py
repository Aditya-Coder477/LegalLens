"""
pipeline/classification/classifier.py
=======================================
Orchestrator that runs keyword classifier first, then optionally falls back
to the LLM classifier for ambiguous documents.

Classification flow:
    Document metadata + text excerpt
        ↓
    Keyword classifier (always runs)
        ↓
    Confidence ≥ threshold?
        ├── YES → final classification (method="keyword")
        └── NO → --enable-llm flag set?
                    ├── NO → mark as "ambiguous" (method="keyword_ambiguous")
                    └── YES → LLM classifier
                                ↓
                             Final classification (method="llm")
"""

from __future__ import annotations

from typing import Optional

from pipeline.core.config import get_config
from pipeline.core.logger import get_logger
from pipeline.core.metadata import LegalDomain
from pipeline.classification.keyword_classifier import classify as keyword_classify

log = get_logger("classifier")


def classify_document(
    title: str,
    subject: str = "",
    ministry: str = "",
    act_number: str = "",
    text_excerpt: str = "",
    enable_llm: Optional[bool] = None,
) -> tuple[str, list[str], float, str]:
    """
    Classify a document into one of 50 legal domains.

    Args:
        title: Document title.
        subject: Subject metadata.
        ministry: Ministry/department string.
        act_number: Act number.
        text_excerpt: First 500 chars of document text (read-only).
        enable_llm: Override config llm_classifier_enabled. None = use config.

    Returns:
        (primary_domain, secondary_domains, confidence, method)
        method is one of: "keyword", "keyword_ambiguous", "llm", "manual"
    """
    cfg = get_config()

    # Step 1: Keyword classifier (always)
    primary, secondary, confidence, _ = keyword_classify(
        title=title,
        subject=subject,
        ministry=ministry,
        act_number=act_number,
        extra_text=text_excerpt,
    )

    # Step 2: If confidence is sufficient, return
    if confidence >= cfg.classification.llm_confidence_threshold:
        log.debug(
            "Classified via keyword",
            title=title[:60], domain=primary, confidence=confidence
        )
        return primary, secondary, confidence, "keyword"

    # Step 3: Low confidence — decide whether to call LLM
    use_llm = enable_llm if enable_llm is not None else cfg.classification.llm_classifier_enabled

    if not use_llm:
        method = "keyword_ambiguous"
        if primary == LegalDomain.UNCLASSIFIED.value:
            log.info(
                "Unclassified document (LLM disabled)",
                title=title[:60],
                note="Run with --enable-llm to attempt LLM classification",
            )
        else:
            log.info(
                "Low-confidence classification (LLM disabled)",
                title=title[:60], domain=primary, confidence=confidence
            )
        return primary, secondary, confidence, method

    # Step 4: LLM fallback
    from pipeline.classification.llm_classifier import classify_with_llm
    log.info(
        "Attempting LLM classification (low keyword confidence)",
        title=title[:60], keyword_confidence=confidence
    )
    llm_result = classify_with_llm(title=title, text_excerpt=text_excerpt)
    if llm_result:
        llm_primary, llm_secondary, llm_confidence, llm_method = llm_result
        log.info(
            "LLM classification complete",
            title=title[:60], domain=llm_primary, confidence=llm_confidence
        )
        return llm_primary, llm_secondary, llm_confidence, llm_method

    # LLM failed — fall back to keyword result
    log.warning(
        "LLM classification failed, using keyword result",
        title=title[:60], domain=primary
    )
    return primary, secondary, confidence, "keyword_ambiguous"
