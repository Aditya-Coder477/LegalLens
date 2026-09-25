"""
pipeline/safety/guardrails.py
=============================
Multi-layer safety guardrails, prompt injection sanitization, and legal ethics
containment for LegalLens Phase 7.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .config import SafetyConfig, get_safety_config
from .models import SafetyViolationType

STANDARD_LEGAL_DISCLAIMER = (
    "LegalLens provides evidence-grounded legal information only and is not a "
    "substitute for professional legal advice from an advocate or attorney."
)

INJECTION_PATTERNS = [
    (r"\b(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous\s+)?instructions\b", SafetyViolationType.PROMPT_INJECTION),
    (r"\b(?:master\s+system\s+prompt|system\s+instruction|system\s+override)\b", SafetyViolationType.PROMPT_INJECTION),
    (r"\b(?:print|reveal|output|display)\s+.*?\b(?:api\s+keys?|passwords?|environment\s+variables?|secret)\b", SafetyViolationType.CONFIDENTIAL_EXFILTRATION),
    (r"\b(?:no\s+longer\s+bound\s+by\s+legal\s+ethics|jailbreak|DAN\s+mode)\b", SafetyViolationType.JAILBREAK),
    (r"\b(?:repeals?\s+the\s+constitution\s+of\s+india|nullifies?\s+all\s+court\s+rulings)\b", SafetyViolationType.PROMPT_INJECTION),
    (r"\b(?:declare\s+(?:party\s+[a-z]|me)\s+to\s+have\s+zero\s+liabilities)\b", SafetyViolationType.UNAUTHORIZED_LEGAL_ADVICE),
]

ADVICE_PATTERNS = [
    (r"\b(?:i\s+advise\s+you\s+to|as\s+your\s+(?:lawyer|advocate|attorney))\b", "Direct counsel representation"),
    (r"\b(?:you\s+will\s+definitely\s+win|guaranteed\s+legal\s+outcome|100%\s+certain\s+to\s+succeed)\b", "Definitive outcome guarantee"),
    (r"\b(?:evade\s+(?:taxes|tax\s+penalties|criminal\s+penalties|statutory\s+fines))\b", "Unlawful evasion encouragement"),
]


class SafetyGuardrails:
    """
    Enforces security, prompt-injection defense, and legal ethics compliance.
    """

    def __init__(self, config: Optional[SafetyConfig] = None):
        self.config = config or get_safety_config()

    def scan_input_for_injection(self, text: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Scan user query or document text for prompt injection attempts.
        Returns: (has_violation, violation_details)
        """
        violations: List[Dict[str, Any]] = []
        t_lower = text.lower()

        for pattern, v_type in INJECTION_PATTERNS:
            match = re.search(pattern, t_lower, re.IGNORECASE)
            if match:
                violations.append({
                    "violation_type": v_type.value,
                    "matched_pattern": match.group(0),
                    "action": "QUARANTINE" if self.config.quarantine_injections else "WARN",
                })

        return len(violations) > 0, violations

    def sanitize_input(self, text: str) -> str:
        """
        Sanitize or neutralize hostile prompt injection payloads inside user input or documents.
        """
        if not self.config.quarantine_injections:
            return text

        sanitized = text
        for pattern, _ in INJECTION_PATTERNS:
            sanitized = re.sub(
                pattern,
                "[REDACTED_SECURITY_PAYLOAD]",
                sanitized,
                flags=re.IGNORECASE,
            )

        # Neutralize explicit tag escape attempts like === END LEGAL EVIDENCE ===
        sanitized = re.sub(
            r"===\s*(?:END|BEGIN)\s+[A-Z\s_]+===",
            "[NEUTRALIZED_DELIMITER_ATTEMPT]",
            sanitized,
        )

        return sanitized

    def scan_output_for_advice(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detect unauthorized legal advice, outcome guarantees, or evasion assistance.
        """
        violations: List[str] = []
        t_lower = text.lower()

        for pattern, desc in ADVICE_PATTERNS:
            match = re.search(pattern, t_lower)
            if match:
                violations.append(f"Detected potential unauthorized legal advice: {desc} ('{match.group(0)}')")

        return len(violations) > 0, violations

    def enforce_guardrails_on_response(
        self,
        response_dict: Dict[str, Any],
        disclaimer_required: bool = True,
    ) -> Dict[str, Any]:
        """
        Apply mandatory guardrail checks to response dictionary.
        """
        # Ensure mandatory disclaimer
        if disclaimer_required:
            if not response_dict.get("disclaimer"):
                response_dict["disclaimer"] = STANDARD_LEGAL_DISCLAIMER

        # Ensure synthetic dataset flags
        if self.config.require_synthetic_watermark:
            response_dict["synthetic"] = True
            response_dict["data_status"] = "SYNTHETIC_DEVELOPMENT_DATA"

        return response_dict
