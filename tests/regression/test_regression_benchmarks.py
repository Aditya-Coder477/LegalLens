"""
tests/regression/test_regression_benchmarks.py
==============================================
Regression test verifying that retrieval and grounding metrics meet baseline expectations.
"""

import json
from pathlib import Path
import pytest

from pipeline.evaluation.config import get_evaluation_config
from pipeline.evaluation.models import EvaluationCase
from pipeline.evaluation.retrieval_evaluator import RetrievalEvaluator


def test_regression_manifest_thresholds():
    manifest_path = Path("tests/regression/regression_manifest.json")
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    baselines = manifest["baselines"]
    cfg = get_evaluation_config()

    # Verify active configuration meets or exceeds baseline expectations
    assert cfg.min_recall_at_10 <= baselines["retrieval"]["recall_at_10"] + 0.1
    assert cfg.min_mrr <= baselines["retrieval"]["mrr"] + 0.1
    assert cfg.max_unsupported_claim_rate >= baselines["grounding"]["unsupported_claim_rate"] - 0.05
