"""
tests/security/test_output_safety.py
====================================
Tests that model outputs are audited for unauthorized legal advice,
definitive outcome guarantees, or tax evasion facilitation.
"""

import pytest

from pipeline.safety.guardrails import SafetyGuardrails


def test_unauthorized_advice_detection():
    guardrails = SafetyGuardrails()

    violating_texts = [
        "As your attorney, I advise you to destroy the financial records.",
        "You will definitely win this writ petition in the High Court 100% guaranteed.",
        "You can evade taxes by transferring proceeds to an offshore shell entity.",
    ]

    for vt in violating_texts:
        has_viol, reasons = guardrails.scan_output_for_advice(vt)
        assert has_viol is True, f"Failed to detect advice violation: {vt}"
        assert len(reasons) > 0


def test_compliant_output_passes():
    guardrails = SafetyGuardrails()

    safe_text = (
        "Under Section 18 of the Digital Lending Act, 2024, entities must register "
        "with the competent authority before commencing operations. Consult legal counsel for specific advice."
    )

    has_viol, reasons = guardrails.scan_output_for_advice(safe_text)
    assert has_viol is False
    assert len(reasons) == 0
