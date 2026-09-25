"""
pipeline/adapters/ecourts.py
==============================
eCourts Adapter — MANUAL IMPORT ONLY.

This adapter makes ZERO HTTP requests to services.ecourts.gov.in.

Reason: Every query on services.ecourts.gov.in requires:
  - Mandatory image CAPTCHA solving
  - Active PHP session (PHPSESSID) binding
  - CSRF/form token validation
  - Risk of IP banning on rapid requests

Bypassing these protections would violate the site's access controls.

Instead, this adapter:
  1. Logs a clear skip record in skipped_sources.csv
  2. Adds detailed instructions to MANUAL_COLLECTION_TODO.md
  3. Points to authorized bulk alternatives:
     - DevDataLab / AWS Open Data — Indian District Courts 2010-2018
     - OpenNyAI corpus (Hugging Face)

Authority tier: OFFICIAL_COURT (when manually imported)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pipeline.core.catalogue import Catalogue
from pipeline.core.logger import get_logger

log = get_logger("ecourts")

SOURCE_NAME = "eCourts Services Portal"
SOURCE_ID = "ecourts"
SKIP_REASON = (
    "mandatory_captcha_and_session_binding — "
    "services.ecourts.gov.in requires CAPTCHA on every query; "
    "automated collection would require bypassing access controls."
)

ALTERNATIVES = [
    {
        "name": "DevDataLab / AWS Open Data — Indian District Courts Dataset 2010-2018",
        "url": "https://registry.opendata.aws/devdatalab-india-courts/",
        "format": "CSV/Parquet",
        "note": "~1TB, contains case metadata, outcomes, judge info for 81M+ cases.",
    },
    {
        "name": "OpenNyAI Legal Corpora (Hugging Face)",
        "url": "https://huggingface.co/opennyaiorg",
        "format": "JSONL/CSV",
        "note": "Curated Indian court judgment datasets for NLP/AI research.",
    },
]

MANUAL_TODO_ENTRY = """
## eCourts — Manual Collection Required

**Source:** services.ecourts.gov.in  
**Reason not automated:** Mandatory image CAPTCHA on every query; PHP session binding; IP banning.  
**Status:** MANUAL IMPORT ONLY

### Recommended Authorized Alternatives

| Source | URL | Format | Notes |
|--------|-----|--------|-------|
| DevDataLab / AWS Open Data (District Courts 2010-2018) | https://registry.opendata.aws/devdatalab-india-courts/ | CSV/Parquet | ~1TB, 81M+ cases |
| OpenNyAI Corpus (Hugging Face) | https://huggingface.co/opennyaiorg | JSONL/CSV | AI-ready NLP datasets |

### How to Import Manually

1. Download a subset from one of the authorized sources above.
2. Use the manual import utility:

```bash
python import_manual.py path/to/downloaded_file.csv \\
  --source ecourts \\
  --doc-type judgment \\
  --domain "Criminal Law" \\
  --title "District Court Judgments 2010-2018" \\
  --url "https://registry.opendata.aws/devdatalab-india-courts/"
```

3. The pipeline will hash, classify, and add the file to the catalogue automatically.

### What NOT to Do

- Do NOT use third-party CAPTCHA-solving services to scrape eCourts
- Do NOT purchase/use automated browser sessions against eCourts
- Do NOT attempt to bypass PHP session validation
"""


async def collect(
    catalogue: Catalogue,
    raw_dir: str = "legal-data/raw/ecourts",
    limit=None,
    resume: bool = True,
    dry_run: bool = False,
    todo_path: str = "MANUAL_COLLECTION_TODO.md",
) -> int:
    """
    eCourts adapter — makes zero HTTP requests.
    Logs skip and updates MANUAL_COLLECTION_TODO.md.

    Returns:
        0 (always — no documents collected automatically)
    """
    log.warning(
        "eCourts adapter: ZERO automated collection",
        reason=SKIP_REASON,
    )

    catalogue.mark_skipped(
        url="https://services.ecourts.gov.in/ecourtindia_v6/",
        source_id=SOURCE_ID,
        reason=SKIP_REASON,
        note="See MANUAL_COLLECTION_TODO.md for authorized alternatives.",
    )

    # Update MANUAL_COLLECTION_TODO.md
    _update_todo(todo_path)

    return 0


def _update_todo(todo_path: str) -> None:
    """Append eCourts section to MANUAL_COLLECTION_TODO.md if not already present."""
    path = Path(todo_path)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if "eCourts — Manual Collection Required" in existing:
            return  # Already added
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n{MANUAL_TODO_ENTRY}\n")
    log.info("Updated MANUAL_COLLECTION_TODO.md with eCourts instructions", path=todo_path)
