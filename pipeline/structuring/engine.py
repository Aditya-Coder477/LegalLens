"""
pipeline/structuring/engine.py
==============================
Phase 3 Orchestration Engine.

Reads:
  legal-data/synthetic/structured/documents.jsonl
  legal-data/synthetic/structured/sections.jsonl
  legal-data/synthetic/metadata/provenance.jsonl

Writes:
  legal-data/synthetic/structured/legal_units.jsonl
  legal-data/synthetic/structured/chunks.jsonl
  legal-data/synthetic/structured/definitions.jsonl
  legal-data/synthetic/structured/cross_references.jsonl
  legal-data/synthetic/structured/chunk_hierarchy.jsonl
  legal-data/synthetic/structured/chunk_statistics.json
  legal-data/synthetic/reports/STRUCTURING_REPORT.md

Processing order (per document):
  1. Load document metadata
  2. Load sections for document
  3. Parse preamble from raw text (acts only)
  4. Parse each section → LegalUnit(s)
  5. Chunk each LegalUnit → ChunkRecord(s)
  6. Extract definitions from each section
  7. Extract cross-references from each LegalUnit
  8. Write all records

Guarantees:
  - synthetic=True and source_authority="SYNTHETIC" on every record
  - Version isolation: never merges chunks from different version_group_ids
  - Resume: skips documents whose chunk_ids are already in chunks.jsonl
  - Stats: produces chunk_statistics.json
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set, Tuple
from uuid import uuid4

from .chunker import LegalChunker, _reset_chunk_counters
from .models import (
    ChunkRecord, ChunkType, CrossReferenceRecord, DefinitionRecord, LegalUnit
)
from .parser import LegalStructureParser, extract_definitions, extract_cross_references
from . import STRUCTURING_VERSION


# ──────────────────────────────────────────────
# JSONL I/O helpers
# ──────────────────────────────────────────────

def _iter_jsonl(path: Path) -> Generator[dict, None, None]:
    """Stream JSONL file, skipping blank lines."""
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _write_jsonl(path: Path, records: List[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


# ──────────────────────────────────────────────
# Structured Corpus Engine
# ──────────────────────────────────────────────

class StructuringEngine:
    """
    Phase 3 orchestrator. Processes all documents in the synthetic corpus
    and produces legal_units.jsonl, chunks.jsonl, definitions.jsonl,
    cross_references.jsonl, and statistics.
    """

    def __init__(
        self,
        synthetic_root: Path,
        output_root: Optional[Path] = None,
        target_tokens: int = 600,
        max_tokens: int = 900,
        min_tokens: int = 100,
        overlap_tokens: int = 50,
        document_type_filter: Optional[str] = None,
        limit: Optional[int] = None,
        overwrite: bool = False,
        resume: bool = True,
        verbose: bool = True,
    ):
        self.synthetic_root      = synthetic_root
        self.output_root         = output_root or (synthetic_root / "structured")
        self.reports_root        = synthetic_root / "reports"
        self.raw_root            = synthetic_root / "raw"

        self.target_tokens       = target_tokens
        self.max_tokens          = max_tokens
        self.min_tokens          = min_tokens
        self.overlap_tokens      = overlap_tokens
        self.document_type_filter = document_type_filter
        self.limit               = limit
        self.overwrite           = overwrite
        self.resume              = resume
        self.verbose             = verbose

        self.chunker  = LegalChunker(target_tokens, max_tokens, min_tokens, overlap_tokens)
        self.parser   = LegalStructureParser(self.raw_root)

        # Output paths
        self.units_path      = self.output_root / "legal_units.jsonl"
        self.chunks_path     = self.output_root / "chunks.jsonl"
        self.defs_path       = self.output_root / "definitions.jsonl"
        self.xrefs_path      = self.output_root / "cross_references.jsonl"
        self.hierarchy_path  = self.output_root / "chunk_hierarchy.jsonl"
        self.stats_path      = self.output_root / "chunk_statistics.json"
        self.report_path     = self.reports_root / "STRUCTURING_REPORT.md"

        # In-memory state
        self.stats: Counter = Counter()
        self.per_type_stats: Dict[str, Counter] = defaultdict(Counter)
        self.errors: List[str] = []
        self.processed_doc_ids: Set[str] = set()
        self._existing_chunk_ids: Set[str] = set()

    def run(self) -> dict:
        """
        Execute the full structuring pipeline.
        Returns a summary statistics dict.
        """
        start_time = time.time()
        self._log("Phase 3: Legal Document Structuring & Chunking started.")

        # Setup output directories
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.reports_root.mkdir(parents=True, exist_ok=True)

        # Load existing state for resume
        if self.resume and not self.overwrite:
            self._load_resume_state()
        elif self.overwrite:
            self._clear_output_files()

        # Always ensure output files exist (even if empty) so downstream tools never fail
        for p in (self.units_path, self.chunks_path, self.defs_path,
                  self.xrefs_path, self.hierarchy_path):
            if not p.exists():
                p.touch()

        # Load provenance map
        prov_map = self._load_provenance_map()

        # Load all sections grouped by document_id
        sections_by_doc = self._load_sections_by_doc()

        # Load all document records
        docs_path = self.output_root.parent / "structured" / "documents.jsonl"
        if not docs_path.exists():
            # Try same dir
            docs_path = self.output_root / "documents.jsonl"
        
        documents = list(_iter_jsonl(docs_path)) if docs_path.exists() else []
        
        if not documents:
            self._log("ERROR: documents.jsonl not found. Aborting.")
            return {"error": "documents.jsonl not found"}

        # Build set of all known doc IDs for cross-ref resolution
        all_doc_ids: Set[str] = {d["document_id"] for d in documents}

        # Filter by type if requested
        if self.document_type_filter:
            documents = [d for d in documents if d.get("document_type") == self.document_type_filter]
            self._log(f"Filtered to {len(documents)} documents of type '{self.document_type_filter}'")

        # Apply limit
        if self.limit:
            documents = documents[: self.limit]

        processed = 0
        for doc in documents:
            doc_id = doc["document_id"]

            # Resume: skip already-processed docs
            if doc_id in self.processed_doc_ids and self.resume and not self.overwrite:
                self._log(f"  [SKIP] {doc_id} (already processed)")
                continue

            try:
                self._process_document(doc, sections_by_doc, prov_map, all_doc_ids)
                processed += 1
                if self.verbose:
                    self._log(f"  [OK] {doc_id}")
            except Exception as exc:
                msg = f"  [ERR] {doc_id}: {exc}"
                self._log(msg)
                self.errors.append(msg)

        elapsed = time.time() - start_time

        # Write statistics
        summary = self._compute_summary(documents, processed, elapsed)
        self._write_stats(summary)
        self._write_report(summary)
        self._print_summary(summary)

        return summary

    # ──────────────────────────────────────────
    # Document Processing
    # ──────────────────────────────────────────

    def _process_document(
        self,
        doc: dict,
        sections_by_doc: Dict[str, List[dict]],
        prov_map: Dict[str, dict],
        all_doc_ids: Set[str],
    ) -> None:
        """Process one document: parse → chunk → extract → write."""
        doc_id   = doc["document_id"]
        doc_type = doc.get("document_type", "other")
        sections = sections_by_doc.get(doc_id, [])

        units: List[LegalUnit]             = []
        chunks: List[ChunkRecord]          = []
        defs: List[dict]                   = []
        xrefs: List[dict]                  = []
        hierarchy: List[dict]              = []
        doc_chunk_ids: Set[str]            = set()

        existing_unit_ids: Dict[str, str] = {}

        # 1. Parse preamble (acts/amendments only)
        if doc_type in ("act", "amendment"):
            raw_path = self._find_raw_path(doc_id, doc_type, doc.get("raw_file_path"))
            if raw_path and raw_path.exists():
                raw_text = raw_path.read_text(encoding="utf-8")
                preamble = self.parser.parse_preamble(doc, raw_text, prov_map)
                if preamble:
                    units.append(preamble)
                    preamble_chunks = self.chunker.chunk_unit(preamble, doc_type, doc_chunk_ids)
                    chunks.extend(preamble_chunks)

        # 2. Parse each section → units
        for sec in sections:
            parsed = self.parser.parse_section(sec, doc, prov_map, existing_unit_ids)
            for u in parsed:
                existing_unit_ids[sec.get("section_id", "")] = u.unit_id
            units.extend(parsed)

            # Definitions from section text
            defs.extend(extract_definitions(sec, doc))

        # 3. Chunk each unit
        for unit in units:
            new_chunks = self.chunker.chunk_unit(unit, doc_type, doc_chunk_ids)
            chunks.extend(new_chunks)

            # Cross-references from unit text
            xrefs.extend(extract_cross_references(unit, all_doc_ids))

        # 4. Build chunk hierarchy
        for unit in units:
            if unit.child_unit_ids:
                for child_id in unit.child_unit_ids:
                    hierarchy.append({
                        "parent_unit_id":   unit.unit_id,
                        "child_unit_id":    child_id,
                        "document_id":      doc_id,
                        "version_group_id": unit.version_group_id,
                        "synthetic":        True,
                        "source_authority": "SYNTHETIC",
                    })

        # 5. Write all records (append mode)
        for unit in units:
            _append_jsonl(self.units_path, unit.model_dump())
        
        for chunk in chunks:
            _append_jsonl(self.chunks_path, chunk.model_dump())
            self._existing_chunk_ids.add(chunk.chunk_id)

        for d in defs:
            d["definition_id"] = str(uuid4())
            _append_jsonl(self.defs_path, d)

        for x in xrefs:
            x["reference_id"] = str(uuid4())
            _append_jsonl(self.xrefs_path, x)

        for h in hierarchy:
            _append_jsonl(self.hierarchy_path, h)

        # 6. Update stats
        self.stats["documents"] += 1
        self.stats["units"]     += len(units)
        self.stats["chunks"]    += len(chunks)
        self.stats["defs"]      += len(defs)
        self.stats["xrefs"]     += len(xrefs)
        self.per_type_stats[doc_type]["documents"] += 1
        self.per_type_stats[doc_type]["chunks"]    += len(chunks)
        self.per_type_stats[doc_type]["units"]     += len(units)
        
        self.processed_doc_ids.add(doc_id)

    # ──────────────────────────────────────────
    # File helpers
    # ──────────────────────────────────────────

    def _find_raw_path(
        self, doc_id: str, doc_type: str, raw_file_path: Optional[str]
    ) -> Optional[Path]:
        """Locate raw text file for a document."""
        if raw_file_path:
            # Try absolute
            p = Path(raw_file_path)
            if p.exists():
                return p
            # Try relative to synthetic root
            p = self.synthetic_root / raw_file_path
            if p.exists():
                return p

        # Infer from doc_id
        if "-ACT-" in doc_id:
            subdir = "acts"
        elif "-RULE-" in doc_id:
            subdir = "rules"
        elif "-NOTIF-" in doc_id:
            subdir = "notifications"
        elif "-GUIDE-" in doc_id:
            subdir = "guidance"
        elif "-JUDG-" in doc_id:
            subdir = "judgments"
        elif "-CONT-" in doc_id:
            subdir = "contracts"
        else:
            return None

        path = self.raw_root / subdir / f"{doc_id}.txt"
        return path if path.exists() else None

    def _load_provenance_map(self) -> Dict[str, dict]:
        """Load provenance records into a dict keyed by document_id."""
        prov_path = self.synthetic_root / "metadata" / "provenance.jsonl"
        prov_map: Dict[str, dict] = {}
        if prov_path.exists():
            for p in _iter_jsonl(prov_path):
                prov_map[p["document_id"]] = p
        return prov_map

    def _load_sections_by_doc(self) -> Dict[str, List[dict]]:
        """Load sections.jsonl into a dict keyed by document_id."""
        secs_path = self.output_root / "sections.jsonl"
        by_doc: Dict[str, List[dict]] = defaultdict(list)
        if secs_path.exists():
            for s in _iter_jsonl(secs_path):
                by_doc[s["document_id"]].append(s)
        return by_doc

    def _load_resume_state(self) -> None:
        """Load previously processed doc IDs from existing chunks.jsonl."""
        if self.chunks_path.exists():
            for chunk in _iter_jsonl(self.chunks_path):
                doc_id = chunk.get("document_id")
                if doc_id:
                    self.processed_doc_ids.add(doc_id)
                chunk_id = chunk.get("chunk_id")
                if chunk_id:
                    self._existing_chunk_ids.add(chunk_id)
            self._log(f"Resume: found {len(self.processed_doc_ids)} already-processed documents.")

    def _clear_output_files(self) -> None:
        """Delete output files for a fresh overwrite run."""
        for p in (self.units_path, self.chunks_path, self.defs_path,
                  self.xrefs_path, self.hierarchy_path):
            if p.exists():
                p.unlink()

    # ──────────────────────────────────────────
    # Statistics & Reporting
    # ──────────────────────────────────────────

    def _compute_summary(self, documents: List[dict], processed: int, elapsed: float) -> dict:
        """Compute final summary statistics."""
        # Read actual counts from written files
        def _count_file(p: Path) -> int:
            if not p.exists():
                return 0
            return sum(1 for _ in p.open(encoding="utf-8") if _.strip())

        def _count_by_type(p: Path, key: str) -> Dict[str, int]:
            counts: Dict[str, int] = Counter()
            if not p.exists():
                return {}
            for line in p.open(encoding="utf-8"):
                line = line.strip()
                if line:
                    r = json.loads(line)
                    counts[r.get(key, "unknown")] += 1
            return dict(counts)

        chunk_count = _count_file(self.chunks_path)
        unit_count  = _count_file(self.units_path)
        def_count   = _count_file(self.defs_path)
        xref_count  = _count_file(self.xrefs_path)
        hier_count  = _count_file(self.hierarchy_path)

        chunks_by_type = _count_by_type(self.chunks_path, "chunk_type")
        chunks_by_doc  = _count_by_type(self.chunks_path, "document_id")

        # Token stats from chunks
        token_counts = []
        if self.chunks_path.exists():
            for line in self.chunks_path.open(encoding="utf-8"):
                if line.strip():
                    r = json.loads(line)
                    tc = r.get("token_count", 0)
                    if tc:
                        token_counts.append(tc)

        avg_tokens = int(sum(token_counts) / len(token_counts)) if token_counts else 0
        min_tokens = min(token_counts) if token_counts else 0
        max_tokens = max(token_counts) if token_counts else 0
        p50 = sorted(token_counts)[len(token_counts) // 2] if token_counts else 0
        p95 = sorted(token_counts)[int(len(token_counts) * 0.95)] if token_counts else 0

        return {
            "generated_at":     datetime.utcnow().isoformat(),
            "structuring_version": STRUCTURING_VERSION,
            "documents_processed":  processed,
            "documents_skipped":    len(documents) - processed,
            "documents_errored":    len(self.errors),
            "legal_units_total":    unit_count,
            "chunks_total":         chunk_count,
            "definitions_total":    def_count,
            "cross_references_total": xref_count,
            "hierarchy_records":    hier_count,
            "chunks_by_type":       dict(sorted(chunks_by_type.items())),
            "chunks_by_doc_type":   dict(self.per_type_stats),
            "token_stats": {
                "min":   min_tokens,
                "max":   max_tokens,
                "avg":   avg_tokens,
                "p50":   p50,
                "p95":   p95,
            },
            "elapsed_seconds":      round(elapsed, 2),
            "errors":               self.errors,
            "synthetic":            True,
            "source_authority":     "SYNTHETIC",
        }

    def _write_stats(self, summary: dict) -> None:
        with self.stats_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    def _write_report(self, summary: dict) -> None:
        lines = [
            "# LegalLens — Phase 3 Structuring Report",
            "",
            "> [!IMPORTANT]",
            "> This report describes a **SYNTHETIC** legal corpus generated for software testing",
            "> and development only. It is NOT real Indian law or authoritative legal information.",
            "",
            f"**Generated:** {summary['generated_at']}",
            f"**Structuring Version:** {summary['structuring_version']}",
            "",
            "## Summary",
            "",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Documents Processed | {summary['documents_processed']} |",
            f"| Documents Skipped (resume) | {summary['documents_skipped']} |",
            f"| Documents Errored | {summary['documents_errored']} |",
            f"| Legal Units | {summary['legal_units_total']} |",
            f"| Chunks | {summary['chunks_total']} |",
            f"| Definitions Extracted | {summary['definitions_total']} |",
            f"| Cross-References Extracted | {summary['cross_references_total']} |",
            f"| Hierarchy Records | {summary['hierarchy_records']} |",
            f"| Elapsed | {summary['elapsed_seconds']}s |",
            "",
            "## Token Statistics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Min Tokens | {summary['token_stats']['min']} |",
            f"| Max Tokens | {summary['token_stats']['max']} |",
            f"| Avg Tokens | {summary['token_stats']['avg']} |",
            f"| P50 Tokens | {summary['token_stats']['p50']} |",
            f"| P95 Tokens | {summary['token_stats']['p95']} |",
            "",
            "## Chunks by Type",
            "",
            "| Chunk Type | Count |",
            "|------------|-------|",
        ]
        for ct, count in sorted(summary["chunks_by_type"].items(), key=lambda x: -x[1]):
            lines.append(f"| {ct} | {count} |")

        if summary["errors"]:
            lines += ["", "## Errors", ""]
            for e in summary["errors"]:
                lines.append(f"- {e}")

        lines += [
            "",
            "---",
            "",
            "> **SYNTHETIC DISCLAIMER**: All documents, legal units, chunks, entities, courts,",
            "> companies, and legal provisions in this corpus are entirely fictional and are",
            "> provided SOLELY for software testing, RAG evaluation, and UI demonstration.",
            "> `source_authority = SYNTHETIC` on every record. `synthetic = true` on every record.",
            "> This corpus must NOT be presented to users as authoritative legal advice.",
        ]

        self.report_path.write_text("\n".join(lines), encoding="utf-8")

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _print_summary(self, summary: dict) -> None:
        print()
        print("=" * 60)
        print("PHASE 3 COMPLETE: Legal Document Structuring & Chunking")
        print("=" * 60)
        print(f"Documents processed : {summary['documents_processed']}")
        print(f"Legal units created : {summary['legal_units_total']}")
        print(f"Chunks created      : {summary['chunks_total']}")
        print(f"Definitions         : {summary['definitions_total']}")
        print(f"Cross-references    : {summary['cross_references_total']}")
        print(f"Elapsed             : {summary['elapsed_seconds']}s")
        print(f"Errors              : {summary['documents_errored']}")
        print()
        print(f"Output directory    : {self.output_root}")
        print(f"Report              : {self.report_path}")
        print(f"Stats               : {self.stats_path}")
        print()
        ts = summary["token_stats"]
        print(f"Token stats (chunks): min={ts['min']}, avg={ts['avg']}, max={ts['max']}, p50={ts['p50']}, p95={ts['p95']}")
        print()
        print("NOTE: All data is SYNTHETIC. source_authority=SYNTHETIC, synthetic=True on all records.")
        print("=" * 60)
