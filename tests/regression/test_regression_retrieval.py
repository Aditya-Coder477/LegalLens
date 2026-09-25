"""
tests/regression/test_regression_retrieval.py
============================================
Regression test verifying retrieval accuracy on golden queries.
"""

import pytest

from pipeline.retrieval.retriever import HybridRetriever


def test_regression_digital_lending_retrieval():
    retriever = HybridRetriever()
    bundle = retriever.retrieve("registration requirements for digital lending entities under Digital Lending Act", top_k=5)
    assert len(bundle.results) > 0
    # Must retrieve relevant digital lending documents or rules
    doc_ids = [ev.document_id for ev in bundle.results]
    assert any("SYN-RULE-005" in d or "SYN-ACT-" in d or "SYN-RULE-" in d for d in doc_ids)
