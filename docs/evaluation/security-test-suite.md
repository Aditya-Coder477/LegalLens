# Security Test Suite & Red-Teaming Methodology

## 1. Overview
The LegalLens Security Test Suite performs automated, deterministic red-teaming across the complete application stack.

## 2. Test Execution
Security tests can be run via:
```bash
python security_test.py --all
```
Or via pytest:
```bash
python -m pytest tests/security/ -v
```

## 3. Test Categories
1. `test_prompt_injection.py`: Direct injection patterns, master overrides, delimiter escapes.
2. `test_jailbreak.py`: Roleplay bypass, DAN jailbreak, illegal legal advice solicitation.
3. `test_canary_leakage.py`: Exfiltration resistance for `CANARY-LEGAL-LENS-123` and internal API keys.
4. `test_pii_leakage.py`: Containment of Aadhaar, PAN, and Indian phone numbers.
5. `test_multi_tenant_isolation.py`: Cross-authority and multi-tenant retrieval boundary enforcement.
6. `test_document_isolation.py`: Ephemeral user document session containment.
7. `test_provenance_tampering.py`: Integrity validation of chunk hashes.
8. `test_citation_tampering.py`: Rejection of dead or forged statutory citations.
9. `test_malformed_inputs.py`: Null bytes, non-UTF8 bytes, SQLi strings.
10. `test_oversized_payloads.py`: Truncation safety for >50,000 word documents.
11. `test_api_auth.py`: Bearer token validation and header enforcement.
12. `test_rate_limits.py`: Token bucket rate limiting under burst queries.
13. `test_output_safety.py`: Detection of unauthorized legal representation and tax evasion advice.
14. `test_security_regression.py`: Regression verification for previously resolved vulnerabilities.
