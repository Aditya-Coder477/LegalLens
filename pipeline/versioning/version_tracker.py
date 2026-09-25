"""
pipeline/versioning/version_tracker.py
========================================
Document version tracking for the LegalLens pipeline.

Groups documents by (normalized_act_title, act_number, act_year) and assigns a
stable document_version_group_id so all versions of the same act can be linked.

Rules:
  - Never overwrites one version with another
  - All versions stored separately
  - Linked via document_version_group_id (UUID5 from group key)
  - Tracks: publication_date, effective_date, amendment_date, repeal_status
"""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from datetime import date
from pathlib import Path
from typing import Optional

from pipeline.core.logger import get_logger
from pipeline.core.metadata import DocumentMetadata, DocumentStatus

log = get_logger("version_tracker")

# Stable namespace for UUID5 generation
_VERSION_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _normalise_act_title(title: str) -> str:
    """Normalise an act title to a stable grouping key."""
    title = unicodedata.normalize("NFKC", title).lower()
    # Remove common variation words
    title = re.sub(r"\b(the|amendment|amending|act|law|ordinance)\b", " ", title)
    title = re.sub(r"\d{4}", "", title)       # Remove years
    title = re.sub(r"[^\w\s]", "", title)    # Remove punctuation
    title = re.sub(r"\s+", " ", title).strip()
    return title


def generate_version_group_id(
    act_title: str,
    act_number: Optional[str] = None,
    jurisdiction: Optional[str] = None,
) -> str:
    """
    Generate a stable document_version_group_id (UUID5) from the act's identity.
    Same legal instrument -> same version group.
    Year, publication date, and amendment dates are version attributes within the group.
    Deterministic: same inputs always -> same UUID.
    """
    norm_title = _normalise_act_title(act_title)
    key_parts = [norm_title]
    if jurisdiction:
        key_parts.append(jurisdiction.strip().lower())
    key = "|".join(key_parts)
    return str(uuid.uuid5(_VERSION_NS, key))



class VersionGroup:
    """All known versions of a single Act/document."""

    def __init__(self, group_id: str, canonical_title: str) -> None:
        self.group_id = group_id
        self.canonical_title = canonical_title
        self.versions: list[dict] = []

    def add_version(self, metadata: DocumentMetadata, version_label: str) -> None:
        self.versions.append({
            "source_id": metadata.source_id,
            "version_label": version_label,
            "publication_date": metadata.publication_date.isoformat() if metadata.publication_date else None,
            "effective_date": metadata.effective_date.isoformat() if metadata.effective_date else None,
            "amendment_date": metadata.amendment_date.isoformat() if metadata.amendment_date else None,
            "repeal_date": metadata.repeal_date.isoformat() if metadata.repeal_date else None,
            "status": metadata.status.value if metadata.status else None,
            "sha256": metadata.sha256,
            "official_url": metadata.official_url,
            "local_path": metadata.local_path,
        })
        log.debug(
            "Version added to group",
            group_id=self.group_id,
            title=self.canonical_title,
            label=version_label,
            version_count=len(self.versions),
        )

    @property
    def is_active(self) -> bool:
        return any(
            v.get("status") == DocumentStatus.ACTIVE.value
            for v in self.versions
        )

    @property
    def is_repealed(self) -> bool:
        return all(
            v.get("status") in (DocumentStatus.REPEALED.value, DocumentStatus.SUPERSEDED.value)
            for v in self.versions
            if v.get("status")
        )


class VersionTracker:
    """
    Manages version groups across the entire corpus.

    Usage:
        tracker = VersionTracker()
        tracker.load(output_dir="legal-data/datasets")

        # When adding a document:
        group_id, label = tracker.assign_version(metadata)
        metadata.document_version_group_id = group_id
        metadata.version_label = label

        tracker.save(output_dir="legal-data/datasets")
    """

    def __init__(self) -> None:
        self._groups: dict[str, VersionGroup] = {}

    def generate_version_group_id(
        self,
        title: str,
        act_year: Optional[int] = None,
        act_number: Optional[str] = None,
        jurisdiction: Optional[str] = None,
    ) -> str:
        return generate_version_group_id(
            act_title=title,
            act_number=act_number,
            jurisdiction=jurisdiction,
        )

    def load(self, output_dir: str = "legal-data/datasets") -> None:
        """Load existing version groups from disk."""
        path = Path(output_dir) / "version_groups.json"
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        for group_data in data.get("groups", []):
            grp = VersionGroup(
                group_id=group_data["group_id"],
                canonical_title=group_data["canonical_title"],
            )
            grp.versions = group_data.get("versions", [])
            self._groups[grp.group_id] = grp
        log.info("Version groups loaded", count=len(self._groups))

    def assign_version(
        self,
        metadata: DocumentMetadata,
    ) -> tuple[str, str]:
        """
        Assign a version_group_id and version_label to a document.
        Adds the document to its version group (creates if new).

        Returns:
            (document_version_group_id, version_label)
        """
        group_id = generate_version_group_id(
            act_title=metadata.title,
            act_number=metadata.act_number,
            jurisdiction=metadata.jurisdiction,
        )

        if group_id not in self._groups:
            self._groups[group_id] = VersionGroup(
                group_id=group_id,
                canonical_title=metadata.title,
            )

        group = self._groups[group_id]

        # Determine version label
        existing_count = len(group.versions)
        if existing_count == 0:
            label = "original"
        elif metadata.amendment_date:
            label = f"amended_{metadata.amendment_date.year}"
        elif metadata.repeal_date:
            label = "repealed"
        else:
            label = f"version_{existing_count + 1}"

        group.add_version(metadata, label)
        return group_id, label

    def save(self, output_dir: str = "legal-data/datasets") -> Path:
        """Persist version groups to version_groups.json."""
        out = Path(output_dir) / "version_groups.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "total_groups": len(self._groups),
            "groups": [
                {
                    "group_id": grp.group_id,
                    "canonical_title": grp.canonical_title,
                    "version_count": len(grp.versions),
                    "versions": grp.versions,
                }
                for grp in self._groups.values()
            ],
        }
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("Version groups saved", path=str(out), groups=len(self._groups))
        return out

    @property
    def groups(self) -> dict[str, VersionGroup]:
        return dict(self._groups)
