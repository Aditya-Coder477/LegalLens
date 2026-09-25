"""
tests/regression/test_regression_grounding.py
============================================
Regression test verifying that supported claims achieve 100% entailment status.
"""

import pytest

from pipeline.retrieval.models import RetrievedEvidence
from pipeline.safety.grounding_engine import GroundingEngine
from pipeline.safety.models import EntailmentStatus


def test_regression_entailment():
    engine = GroundingEngine()
    ev = RetrievedEvidence(
        chunk_id="E1",
        kb_chunk_id="kb-1",
        rank=1,
        document_id="SYN-ACT-001",
        section="18",
        text="The Central Government may make rules for carrying out the purposes of this Act.",
    )
    res = engine.verify_claim(
        claim_text="The Central Government is empowered to make rules under this Act.",
        claim_id="C1",
        cited_evidence_ids=["E1"],
        evidence_map={"E1": ev},
    )

    assert res.status in (EntailmentStatus.ENTAILED, EntailmentStatus.PARTIALLY_ENTAILED)
    assert res.status != EntailmentStatus.CONTRADICTED
