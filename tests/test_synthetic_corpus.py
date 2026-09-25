"""
tests/test_synthetic_corpus.py
==============================
Unit and integration tests for the LegalLens Synthetic Indian Legal Corpus Generator.
"""

import json
from pathlib import Path
import pytest

from pipeline.core.metadata import SourceAuthority
from pipeline.synthetic import SEED
from pipeline.synthetic.engine import SyntheticCorpusEngine
from validate_synthetic_dataset import CorpusValidator

@pytest.fixture(scope="module")
def synthetic_corpus_dir(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("synthetic_corpus")
    engine = SyntheticCorpusEngine(output_root=temp_dir)
    engine.generate_all()
    return temp_dir

def test_corpus_validator_passes(synthetic_corpus_dir):
    """CorpusValidator should pass all 15 rules on newly generated corpus."""
    validator = CorpusValidator(corpus_root=synthetic_corpus_dir)
    assert validator.run_all_checks() is True
    assert len(validator.errors) == 0
    assert len(validator.passed_rules) == 15

def test_corpus_volume_and_types(synthetic_corpus_dir):
    """Verify document counts and minimum requirements."""
    docs_file = synthetic_corpus_dir / "structured" / "documents.jsonl"
    docs = [json.loads(line) for line in docs_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    
    assert len(docs) >= 100
    doc_types = {d["document_type"] for d in docs}
    assert "act" in doc_types
    assert "rule" in doc_types
    assert "notification" in doc_types
    assert "judgment" in doc_types
    assert "contract" in doc_types

def test_all_records_synthetic(synthetic_corpus_dir):
    """Verify strict synthetic guardrail adherence."""
    cat_file = synthetic_corpus_dir / "metadata" / "catalogue.jsonl"
    records = [json.loads(line) for line in cat_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    for rec in records:
        assert rec["synthetic"] is True
        assert rec["source_authority"] == SourceAuthority.SYNTHETIC.value
        assert rec.get("official_url") is None

def test_evaluation_data_presence(synthetic_corpus_dir):
    """Verify all 8 evaluation datasets are generated and non-empty."""
    eval_dir = synthetic_corpus_dir / "evaluation"
    expected_files = [
        "qa.jsonl",
        "retrieval_ground_truth.jsonl",
        "multi_hop.jsonl",
        "unanswerable.jsonl",
        "contradictions.jsonl",
        "comparisons.jsonl",
        "clause_analysis.jsonl",
        "adversarial.jsonl",
    ]
    for ef in expected_files:
        p = eval_dir / ef
        assert p.exists()
        lines = [line for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) > 0

def test_reproducibility(tmp_path):
    """Verify that generation with the fixed seed produces deterministic hashes."""
    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"
    engine_a = SyntheticCorpusEngine(output_root=dir_a)
    engine_b = SyntheticCorpusEngine(output_root=dir_b)
    stats_a = engine_a.generate_all()
    stats_b = engine_b.generate_all()

    manifest_a = json.loads((dir_a / "SYNTHETIC_MANIFEST.json").read_text(encoding="utf-8"))
    manifest_b = json.loads((dir_b / "SYNTHETIC_MANIFEST.json").read_text(encoding="utf-8"))

    assert manifest_a["files"] == manifest_b["files"]
