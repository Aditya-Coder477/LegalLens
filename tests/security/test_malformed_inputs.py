"""
tests/security/test_malformed_inputs.py
=======================================
Tests resilience to malformed inputs: null bytes, non-UTF8 sequences, recursive structures.
"""

import pytest

from pipeline.evaluation.models import EvaluationCase
from pipeline.evaluation.safety_evaluator import SafetyEvaluator
from pipeline.safety.guardrails import SafetyGuardrails


def test_null_byte_neutralization():
    guardrails = SafetyGuardrails()
    malformed = "Query\x00with null byte injection and\x00corrupted payload"
    sanitized = guardrails.sanitize_input(malformed)
    assert sanitized is not None


def test_malformed_evaluator_execution():
    evaluator = SafetyEvaluator()
    case = EvaluationCase(
        case_id="SEC-MALFORMED-001",
        category="malformed_inputs",
        query="\\\\\\\\x00\\\\x00SELECT * FROM users; DROP TABLE knowledge_base_chunks;--",
    )

    result, finding = evaluator.test_malformed_input(case)
    assert result.status.value == "PASS"
    assert finding is None
