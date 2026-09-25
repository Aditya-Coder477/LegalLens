"""
pipeline/classification/llm_classifier.py
==========================================
Optional LLM-assisted legal domain classifier.

Activated only when:
  1. --enable-llm CLI flag is set, OR config.classification.llm_classifier_enabled = true
  2. Keyword classifier confidence < config.classification.llm_confidence_threshold
  3. LLM_API_KEY is set in environment

Rules:
  - NEVER modifies source text
  - Uses only: document title + first 500 chars of text
  - API key from environment variable LLM_API_KEY (never hard-coded)
  - Provider-agnostic: supports google, openai, anthropic
  - Returns None gracefully if API is unavailable
"""

from __future__ import annotations

import json
import os
from typing import Optional

from pipeline.core.logger import get_logger
from pipeline.core.metadata import LegalDomain

log = get_logger("llm_classifier")

LEGAL_DOMAINS_LIST = [d.value for d in LegalDomain if d != LegalDomain.UNCLASSIFIED]

_PROMPT_TEMPLATE = """You are a legal document classifier for Indian law.

Given the document title and a brief excerpt, identify the most relevant legal domain(s).

Document title: {title}
Excerpt (first 500 chars): {excerpt}

Available legal domains:
{domains}

Respond ONLY with a JSON object in this exact format:
{{
  "primary_domain": "<domain name from list above>",
  "secondary_domains": ["<domain>", "<domain>"],
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence>"
}}

IMPORTANT:
- Use domain names EXACTLY as listed above
- secondary_domains can be empty []
- Do NOT add any text outside the JSON
- Do NOT modify or interpret the source text
"""


def classify_with_llm(
    title: str,
    text_excerpt: str,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[tuple[str, list[str], float, str]]:
    """
    Classify a document using an LLM.

    Args:
        title: Document title.
        text_excerpt: First 500 characters of document text (read-only, not modified).
        provider: 'google', 'openai', or 'anthropic'. Reads LLM_PROVIDER from env if None.
        api_key: API key. Reads LLM_API_KEY from env if None.
        model: Model name. Reads LLM_MODEL from env if None.

    Returns:
        (primary_domain, secondary_domains, confidence, "llm") or None on failure.
    """
    provider = (provider or os.environ.get("LLM_PROVIDER", "google")).lower().strip()
    api_key = api_key or os.environ.get("LLM_API_KEY", "")
    model = model or os.environ.get("LLM_MODEL", "")

    if not api_key:
        log.warning(
            "LLM classifier skipped — LLM_API_KEY not set",
            note="Set LLM_API_KEY in .env to enable LLM classification",
        )
        return None

    domains_str = "\n".join(f"  - {d}" for d in LEGAL_DOMAINS_LIST)
    prompt = _PROMPT_TEMPLATE.format(
        title=title[:300],
        excerpt=text_excerpt[:500],
        domains=domains_str,
    )

    try:
        raw_response = _call_provider(provider, api_key, model, prompt)
    except Exception as exc:
        log.error("LLM API call failed", provider=provider, error=str(exc))
        return None

    return _parse_response(raw_response)


def _call_provider(provider: str, api_key: str, model: str, prompt: str) -> str:
    """Call the appropriate LLM provider and return the raw text response."""
    if provider == "google":
        return _call_google(api_key, model or "gemini-1.5-flash", prompt)
    elif provider == "openai":
        return _call_openai(api_key, model or "gpt-4o-mini", prompt)
    elif provider == "anthropic":
        return _call_anthropic(api_key, model or "claude-3-haiku-20240307", prompt)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Use 'google', 'openai', or 'anthropic'.")


def _call_google(api_key: str, model: str, prompt: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError as e:
        raise ImportError(
            "google-generativeai package required. Install: pip install google-generativeai"
        ) from e
    genai.configure(api_key=api_key)
    m = genai.GenerativeModel(model)
    response = m.generate_content(prompt)
    return response.text


def _call_openai(api_key: str, model: str, prompt: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ImportError("openai package required. Install: pip install openai") from e
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(api_key: str, model: str, prompt: str) -> str:
    try:
        import anthropic
    except ImportError as e:
        raise ImportError("anthropic package required. Install: pip install anthropic") from e
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _parse_response(
    raw: str,
) -> Optional[tuple[str, list[str], float, str]]:
    """Parse LLM JSON response into (primary_domain, secondary_domains, confidence, 'llm')."""
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find JSON block in the response
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            log.error("LLM response could not be parsed as JSON", raw=raw[:200])
            return None
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return None

    primary = data.get("primary_domain", "")
    secondary = data.get("secondary_domains", [])
    confidence = float(data.get("confidence", 0.5))

    # Validate primary domain against known list
    valid_domains = {d.value for d in LegalDomain}
    if primary not in valid_domains:
        log.warning("LLM returned unknown domain", domain=primary)
        primary = LegalDomain.UNCLASSIFIED.value
        confidence = 0.0

    # Filter secondary domains
    secondary = [d for d in (secondary or []) if d in valid_domains][:4]

    return primary, secondary, confidence, "llm"
