# Legal AI Threat Model

## 1. Scope & Objective
This document outlines the formal threat model for the **LegalLens** GenAI platform, an India-first legal information assistant.

## 2. Threat Actors & Capabilities
- **Adversarial Users**: Attempting prompt injections, jailbreaks, extracting canary keys, or eliciting unauthorized legal representation.
- **Untrusted Document Uploads**: Ephemeral contracts or user-provided files embedding indirect prompt injections or delimiter breakout tokens.
- **Cross-Tenant Attackers**: Users attempting to query or exfiltrate another tenant's confidential documents or regulatory files.

## 3. Attack Surface & Mitigations

| Threat Vector | Severity | Attack Technique | LegalLens Mitigation |
|---|---|---|---|
| **Direct Prompt Injection** | HIGH | "Ignore previous instructions", "SYSTEM OVERRIDE" | `SafetyGuardrails.scan_input_for_injection` + regex neutralization |
| **Indirect Prompt Injection** | HIGH | Hidden text in uploaded contracts / comments | XML/Delimited prompt segregation in `ContextBuilder` |
| **Jailbreak / Persona Switch** | HIGH | "DAN mode", hypothetical crime scenarios | System prompt role lock + `scan_output_for_advice` |
| **Canary Secret Exfiltration** | CRITICAL | Attempting to print internal environment tokens | Post-generation regex scrubbing + canary monitoring |
| **Indian PII Leakage** | HIGH | Extraction of Aadhaar, PAN, phone numbers | Automatic PII masking in output validator |
| **Cross-Tenant Breach** | CRITICAL | Querying across tenant boundaries | Enforced SQL predicates in `lexical_retriever` & `semantic_retriever` |
| **Citation / Provenance Forgery**| MEDIUM | Hallucinating fake sections or altered hashes | Cryptographic SHA-256 verification against immutable KB |
| **Malformed / Oversized Payload**| MEDIUM | ReDoS, null bytes, >10MB files | Input sanitization, token budgeting, and boundary limits |
