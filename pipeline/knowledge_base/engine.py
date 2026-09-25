"""
pipeline/knowledge_base/engine.py
=================================
Orchestration engine for Phase 4: Knowledge Base + Embeddings.
Manages input ingestion, batch embedding, cache reuse, DB storage,
manifest generation, and quality reporting.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple
from uuid import uuid4

from .cache import EmbeddingCacheManager
from .config import get_kb_config
from .db import DatabaseManager
from .db_models import (
    EmbeddingTable,
    IngestionRunTable,
    KBCrossRefTable,
    KBDefinitionTable,
    KBChunkTable,
)
from .hashing import compute_content_hash, compute_vector_hash
from .models import (
    EmbeddingManifest,
    EmbeddingRecord,
    EmbeddingStats,
    KBQualityReport,
    KnowledgeBaseChunk,
    KnowledgeBaseManifest,
)
from .providers import EmbeddingProvider, get_embedding_provider, validate_vector


def _stream_jsonl(path: Path) -> Generator[Dict[str, Any], None, None]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _append_jsonl(path: Path, data: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")


class KnowledgeBaseEngine:
    """
    Main Phase 4 Knowledge Base Orchestration Engine.
    """

    def __init__(
        self,
        chunks_path: Optional[Path] = None,
        kb_data_path: Optional[Path] = None,
        db_url: Optional[str] = None,
        provider: Optional[EmbeddingProvider] = None,
        batch_size: Optional[int] = None,
        limit: Optional[int] = None,
        document_type_filter: Optional[str] = None,
        source_authority_filter: Optional[str] = None,
        resume: bool = True,
        overwrite: bool = False,
        dry_run: bool = False,
        verbose: bool = True,
    ):
        cfg = get_kb_config()
        self.chunks_path = chunks_path or cfg.structured_chunks_path
        self.kb_data_path = kb_data_path or cfg.kb_data_path
        self.batch_size = batch_size or cfg.embedding_batch_size
        self.limit = limit
        self.document_type_filter = document_type_filter
        self.source_authority_filter = source_authority_filter
        self.resume = resume
        self.overwrite = overwrite
        self.dry_run = dry_run
        self.verbose = verbose

        # Setup subdirectories
        self.manifests_dir = self.kb_data_path / "manifests"
        self.canonical_dir = self.kb_data_path / "canonical"
        self.embeddings_dir = self.kb_data_path / "embeddings"
        self.exports_dir = self.kb_data_path / "exports"
        self.reports_dir = self.kb_data_path / "reports"

        for d in (
            self.manifests_dir,
            self.canonical_dir,
            self.embeddings_dir,
            self.exports_dir,
            self.reports_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

        self.canonical_chunks_path = self.canonical_dir / "kb_chunks.jsonl"
        self.embedding_errors_path = self.embeddings_dir / "embedding_errors.jsonl"
        self.embedding_stats_path = self.embeddings_dir / "embedding_stats.json"
        self.embedding_cache_path = self.embeddings_dir / "embedding_cache.json"
        self.kb_snapshot_path = self.exports_dir / "kb_snapshot.jsonl"
        self.kb_manifest_path = self.manifests_dir / "knowledge_base_manifest.json"
        self.emb_manifest_path = self.manifests_dir / "embedding_manifest.json"
        self.quality_report_json = self.reports_dir / "kb_quality_report.json"
        self.quality_report_md = self.reports_dir / "kb_quality_report.md"
        self.emb_report_md = self.reports_dir / "embedding_report.md"

        self.db = DatabaseManager(db_url)
        self.cache = EmbeddingCacheManager(self.embedding_cache_path)
        self.provider = provider or get_embedding_provider(
            provider_name=cfg.embedding_provider,
            model_name=cfg.embedding_model,
            dimension=cfg.embedding_dimension,
            api_key=cfg.openai_api_key,
            base_url=cfg.openai_base_url,
            normalize=cfg.normalize_embeddings,
        )

    def log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def ingest(self) -> Dict[str, Any]:
        """
        Run the complete Knowledge Base ingestion pipeline.
        """
        start_time = datetime.utcnow()
        run_id = f"run-{uuid4().hex[:8]}"
        self.log(f"Phase 4: Knowledge Base Ingestion started [run_id: {run_id}]")

        if not self.dry_run:
            self.db.init_db()

        if self.overwrite and not self.dry_run:
            if self.canonical_chunks_path.exists():
                self.canonical_chunks_path.unlink()
            if self.embedding_errors_path.exists():
                self.embedding_errors_path.unlink()

        # Track existing processed chunks if resuming
        existing_processed_chunks: Set[str] = set()
        if self.resume and not self.overwrite and self.canonical_chunks_path.exists():
            for row in _stream_jsonl(self.canonical_chunks_path):
                cid = row.get("chunk_id")
                if cid:
                    existing_processed_chunks.add(cid)
            self.log(f"Resuming: found {len(existing_processed_chunks)} previously ingested chunks.")

        # Read and filter chunks
        candidates: List[Dict[str, Any]] = []
        for c in _stream_jsonl(self.chunks_path):
            if self.document_type_filter:
                # doc type matching
                if self.document_type_filter.lower() not in c.get("chunk_type", "").lower() and \
                   self.document_type_filter.lower() not in c.get("document_id", "").lower():
                    continue
            if self.source_authority_filter:
                if c.get("source_authority") != self.source_authority_filter:
                    continue
            candidates.append(c)
            if self.limit and len(candidates) >= self.limit:
                break

        total_input_chunks = len(candidates)
        self.log(f"Loaded {total_input_chunks} candidate chunks for processing.")

        new_embeddings = 0
        reused_embeddings = 0
        failed_embeddings = 0
        skipped_chunks = 0
        processed_kb_chunks: List[KnowledgeBaseChunk] = []

        # Process in batches
        batches = [candidates[i : i + self.batch_size] for i in range(0, len(candidates), self.batch_size)]

        with self.db.session_scope() as session:
            for b_idx, batch in enumerate(batches, 1):
                texts_to_embed: List[str] = []
                batch_kb_chunks: List[KnowledgeBaseChunk] = []
                batch_need_embed_indices: List[int] = []

                for item in batch:
                    chunk_id = item["chunk_id"]

                    if chunk_id in existing_processed_chunks and self.resume and not self.overwrite:
                        skipped_chunks += 1
                        continue

                    text = item.get("text", "")
                    emb_text = item.get("embedding_text", "") or text
                    c_hash = compute_content_hash(
                        text=text,
                        title=item.get("title"),
                        document_id=item.get("document_id"),
                        section_number=item.get("section_number"),
                        embedding_text=emb_text,
                    )

                    kb_chunk = KnowledgeBaseChunk(
                        kb_chunk_id=f"kb-{chunk_id}",
                        chunk_id=chunk_id,
                        document_id=item["document_id"],
                        version_group_id=item.get("version_group_id"),
                        version_id=item.get("version_id"),
                        chunk_type=item.get("chunk_type", "SECTION"),
                        title=item.get("title"),
                        chapter=item.get("chapter_title"),
                        section=item.get("section_number"),
                        subsection=item.get("subsection_number"),
                        clause=item.get("clause_number"),
                        parent_unit_id=item.get("parent_unit_id"),
                        text=text,
                        embedding_text=emb_text,
                        page_start=item.get("page_start"),
                        page_end=item.get("page_end"),
                        token_count=item.get("token_count", 0),
                        legal_domains=item.get("legal_domains", []),
                        synthetic=bool(item.get("synthetic", True)),
                        source_authority=item.get("source_authority", "SYNTHETIC"),
                        source_document_id=item.get("source_document_id"),
                        source_sha256=item.get("source_sha256"),
                        provenance_id=item.get("provenance_id"),
                        embedding_provider=self.provider.provider_name,
                        embedding_model=self.provider.model_name,
                        embedding_dimension=self.provider.dimension,
                        content_hash=c_hash,
                    )

                    # Check cache or DB for existing embedding (Section 13)
                    cached_vec = self.cache.get(
                        c_hash,
                        self.provider.provider_name,
                        self.provider.model_name,
                        self.provider.dimension,
                    )
                    if cached_vec is None and not self.dry_run:
                        cached_vec = self.db.get_embedding_by_hash(
                            c_hash,
                            self.provider.provider_name,
                            self.provider.model_name,
                            self.provider.dimension,
                            session,
                        )

                    if cached_vec is not None:
                        reused_embeddings += 1
                        kb_chunk.embedding_hash = compute_vector_hash(cached_vec)
                        kb_chunk.embedding_created_at = datetime.utcnow().isoformat()
                        if not self.dry_run:
                            emb_record = EmbeddingRecord(
                                kb_chunk_id=kb_chunk.kb_chunk_id,
                                chunk_id=kb_chunk.chunk_id,
                                content_hash=c_hash,
                                provider=self.provider.provider_name,
                                model=self.provider.model_name,
                                dimension=self.provider.dimension,
                                vector=cached_vec,
                                embedding_hash=kb_chunk.embedding_hash,
                            )
                            self.db.upsert_embedding(emb_record, session)
                    else:
                        batch_need_embed_indices.append(len(batch_kb_chunks))
                        texts_to_embed.append(emb_text)

                    batch_kb_chunks.append(kb_chunk)

                # Generate new embeddings in batch if any
                if texts_to_embed and not self.dry_run:
                    try:
                        generated_vecs = self.provider.embed_batch(texts_to_embed)
                        for idx, vec in zip(batch_need_embed_indices, generated_vecs):
                            validate_vector(vec, self.provider.dimension)
                            ch = batch_kb_chunks[idx]
                            v_hash = compute_vector_hash(vec)
                            ch.embedding_hash = v_hash
                            ch.embedding_created_at = datetime.utcnow().isoformat()

                            self.cache.put(
                                ch.content_hash,
                                self.provider.provider_name,
                                self.provider.model_name,
                                self.provider.dimension,
                                vec,
                            )

                            emb_record = EmbeddingRecord(
                                kb_chunk_id=ch.kb_chunk_id,
                                chunk_id=ch.chunk_id,
                                content_hash=ch.content_hash,
                                provider=self.provider.provider_name,
                                model=self.provider.model_name,
                                dimension=self.provider.dimension,
                                vector=vec,
                                embedding_hash=v_hash,
                            )
                            self.db.upsert_embedding(emb_record, session)
                            new_embeddings += 1
                    except Exception as err:
                        failed_embeddings += len(texts_to_embed)
                        error_entry = {
                            "run_id": run_id,
                            "batch_index": b_idx,
                            "error": str(err),
                            "timestamp": datetime.utcnow().isoformat(),
                            "chunk_ids": [batch_kb_chunks[i].chunk_id for i in batch_need_embed_indices],
                        }
                        _append_jsonl(self.embedding_errors_path, error_entry)

                # Store KB chunks
                for kb_chunk in batch_kb_chunks:
                    if not self.dry_run:
                        self.db.upsert_chunk(kb_chunk, session)
                        _append_jsonl(self.canonical_chunks_path, kb_chunk.model_dump())
                        _append_jsonl(self.kb_snapshot_path, kb_chunk.model_dump())
                    processed_kb_chunks.append(kb_chunk)

                if self.verbose and b_idx % 5 == 0:
                    self.log(f"  Processed batch {b_idx}/{len(batches)} ({len(processed_kb_chunks)} chunks)")

        # Save cache to disk
        if not self.dry_run:
            self.cache.save()

            # Ingest definitions & cross references from Phase 3 into KB relational tables
            self._ingest_auxiliary_records()

        end_time = datetime.utcnow()
        elapsed = (end_time - start_time).total_seconds()

        # Ingestion run record in DB
        if not self.dry_run:
            with self.db.session_scope() as session:
                run_row = IngestionRunTable(
                    run_id=run_id,
                    started_at=start_time.isoformat(),
                    completed_at=end_time.isoformat(),
                    total_chunks=len(processed_kb_chunks),
                    new_embeddings=new_embeddings,
                    reused_embeddings=reused_embeddings,
                    failed_embeddings=failed_embeddings,
                    status="completed" if failed_embeddings == 0 else "partial",
                )
                session.add(run_row)

        summary = {
            "run_id": run_id,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "total_input_chunks": total_input_chunks,
            "processed_chunks": len(processed_kb_chunks),
            "skipped_chunks": skipped_chunks,
            "new_embeddings": new_embeddings,
            "reused_embeddings": reused_embeddings,
            "failed_embeddings": failed_embeddings,
            "dry_run": self.dry_run,
            "provider": self.provider.provider_name,
            "model": self.provider.model_name,
            "dimension": self.provider.dimension,
            "status": "success" if failed_embeddings == 0 else "completed_with_errors",
        }

        # Generate manifests and reports
        if not self.dry_run:
            self._generate_manifests_and_reports(summary, processed_kb_chunks)

        self._print_ingestion_summary(summary)
        return summary

    def _ingest_auxiliary_records(self) -> None:
        """
        Link and ingest Phase 3 definitions and cross-references into Knowledge Base tables.
        """
        structured_dir = self.chunks_path.parent
        defs_file = structured_dir / "definitions.jsonl"
        xrefs_file = structured_dir / "cross_references.jsonl"

        with self.db.session_scope() as session:
            if defs_file.exists():
                for d in _stream_jsonl(defs_file):
                    def_id = d.get("definition_id") or str(uuid4())
                    exists = session.query(KBDefinitionTable).filter_by(definition_id=def_id).first()
                    if not exists:
                        session.add(KBDefinitionTable(
                            definition_id=def_id,
                            document_id=d.get("document_id", ""),
                            term=d.get("term", ""),
                            definition_text=d.get("definition_text", ""),
                            source_section_id=d.get("source_section_id"),
                            synthetic=d.get("synthetic", True),
                            source_authority=d.get("source_authority", "SYNTHETIC"),
                        ))

            if xrefs_file.exists():
                for x in _stream_jsonl(xrefs_file):
                    ref_id = x.get("reference_id") or str(uuid4())
                    exists = session.query(KBCrossRefTable).filter_by(reference_id=ref_id).first()
                    if not exists:
                        session.add(KBCrossRefTable(
                            reference_id=ref_id,
                            source_unit_id=x.get("source_unit_id", ""),
                            source_document_id=x.get("source_document_id", ""),
                            target_reference=x.get("target_reference", ""),
                            reference_type=x.get("reference_type", ""),
                            resolved_target_document_id=x.get("resolved_target_document_id"),
                            synthetic=x.get("synthetic", True),
                            source_authority=x.get("source_authority", "SYNTHETIC"),
                        ))

    def _generate_manifests_and_reports(
        self,
        summary: Dict[str, Any],
        chunks: List[KnowledgeBaseChunk],
    ) -> None:
        # Calculate SHA256 of input chunks file
        input_sha256 = ""
        if self.chunks_path.exists():
            import hashlib
            input_sha256 = hashlib.sha256(self.chunks_path.read_bytes()).hexdigest()

        # Embedding Manifest (Section 22)
        emb_manifest = EmbeddingManifest(
            run_id=summary["run_id"],
            started_at=summary["started_at"],
            completed_at=summary["completed_at"],
            input_file=str(self.chunks_path),
            input_sha256=input_sha256,
            total_chunks=summary["processed_chunks"],
            new_embeddings=summary["new_embeddings"],
            reused_embeddings=summary["reused_embeddings"],
            failed_embeddings=summary["failed_embeddings"],
            skipped_embeddings=summary["skipped_chunks"],
            provider=summary["provider"],
            model=summary["model"],
            dimension=summary["dimension"],
            synthetic_chunk_count=sum(1 for c in chunks if c.synthetic),
            non_synthetic_chunk_count=sum(1 for c in chunks if not c.synthetic),
            database_target=self.db.engine.dialect.name,
            status=summary["status"],
        )
        self.emb_manifest_path.write_text(emb_manifest.model_dump_json(indent=2), encoding="utf-8")

        # Embedding Stats (Section 35)
        emb_stats = EmbeddingStats(
            total_chunks=summary["processed_chunks"],
            embedded=summary["new_embeddings"] + summary["reused_embeddings"],
            failed=summary["failed_embeddings"],
            reused=summary["reused_embeddings"],
            new=summary["new_embeddings"],
            dimension=summary["dimension"],
            provider=summary["provider"],
            model=summary["model"],
        )
        self.embedding_stats_path.write_text(emb_stats.model_dump_json(indent=2), encoding="utf-8")

        # Knowledge Base Manifest (Section 23)
        doc_ids = {c.document_id for c in chunks}
        version_ids = {c.version_id for c in chunks if c.version_id}
        kb_manifest = KnowledgeBaseManifest(
            created_at=summary["started_at"],
            updated_at=summary["completed_at"],
            source_corpus="synthetic",
            source_corpus_sha256=input_sha256,
            total_documents=len(doc_ids),
            total_versions=len(version_ids),
            total_legal_units=sum(1 for c in chunks if c.parent_unit_id),
            total_chunks=len(chunks),
            total_embeddings=emb_stats.embedded,
            embedding_provider=summary["provider"],
            embedding_model=summary["model"],
            embedding_dimension=summary["dimension"],
            synthetic_documents=len(doc_ids),
            official_documents=0,
            user_documents=0,
        )
        self.kb_manifest_path.write_text(kb_manifest.model_dump_json(indent=2), encoding="utf-8")

        # Quality Report (Section 34)
        tokens = [c.token_count for c in chunks] or [0]
        chunk_types = Counter(c.chunk_type for c in chunks)
        domains = Counter(d for c in chunks for d in c.legal_domains)

        quality_report = KBQualityReport(
            documents=len(doc_ids),
            versions=len(version_ids),
            legal_units=sum(1 for c in chunks if c.parent_unit_id),
            chunks=len(chunks),
            embedded_chunks=emb_stats.embedded,
            missing_embeddings=len(chunks) - emb_stats.embedded,
            failed_embeddings=summary["failed_embeddings"],
            synthetic_chunks=sum(1 for c in chunks if c.synthetic),
            official_chunks=0,
            user_chunks=0,
            chunk_types=dict(chunk_types),
            legal_domains=dict(domains),
            average_tokens=round(sum(tokens) / len(tokens), 2),
            min_tokens=min(tokens),
            max_tokens=max(tokens),
            embedding_dimension=summary["dimension"],
            embedding_model=summary["model"],
            duplicate_content_hashes=len(chunks) - len({c.content_hash for c in chunks}),
            orphan_records=0,
            missing_provenance=sum(1 for c in chunks if not c.provenance_id),
            database_status="healthy",
            embedding_coverage=round(emb_stats.embedded / len(chunks), 4) if chunks else 1.0,
        )
        self.quality_report_json.write_text(quality_report.model_dump_json(indent=2), encoding="utf-8")

        # Human-readable markdown reports
        self._write_markdown_reports(summary, quality_report)

    def _write_markdown_reports(self, summary: Dict[str, Any], qr: KBQualityReport) -> None:
        md_kb = [
            "# LegalLens — Knowledge Base Quality Report",
            "",
            "> [!IMPORTANT]",
            "> All corpus records are **SYNTHETIC** (`source_authority = SYNTHETIC`, `synthetic = true`).",
            "> This dataset is for software engineering, RAG testing, and retrieval evaluation only.",
            "",
            f"**Generated:** {qr.generated_at}  ",
            f"**Database:** {self.db.engine.dialect.name}  ",
            f"**Embedding Model:** {qr.embedding_model} ({qr.embedding_dimension}d)  ",
            f"**Embedding Coverage:** {qr.embedding_coverage * 100:.2f}%  ",
            "",
            "## Corpus Overview",
            "",
            f"| Metric | Count |",
            f"| --- | --- |",
            f"| Total Documents | {qr.documents} |",
            f"| Distinct Versions | {qr.versions} |",
            f"| Total Chunks | {qr.chunks} |",
            f"| Embedded Chunks | {qr.embedded_chunks} |",
            f"| Missing Embeddings | {qr.missing_embeddings} |",
            f"| Failed Embeddings | {qr.failed_embeddings} |",
            f"| Synthetic Chunks | {qr.synthetic_chunks} |",
            f"| Average Tokens | {qr.average_tokens} |",
            f"| Min / Max Tokens | {qr.min_tokens} / {qr.max_tokens} |",
            "",
            "## Chunk Distribution by Type",
            "",
            "| Chunk Type | Count |",
            "| --- | --- |",
        ]
        for ct, n in sorted(qr.chunk_types.items(), key=lambda x: -x[1]):
            md_kb.append(f"| {ct} | {n} |")

        md_kb.extend([
            "",
            "---",
            "*LegalLens Phase 4 Knowledge Base — Ready for Phase 5 Hybrid RAG & Retrieval.*",
        ])
        self.quality_report_md.write_text("\n".join(md_kb), encoding="utf-8")

        # Embedding report
        md_emb = [
            "# LegalLens — Embedding Ingestion Report",
            "",
            f"**Run ID:** `{summary['run_id']}`  ",
            f"**Provider:** `{summary['provider']}`  ",
            f"**Model:** `{summary['model']}`  ",
            f"**Dimension:** `{summary['dimension']}`  ",
            f"**Elapsed Time:** `{summary['elapsed_seconds']}s`  ",
            "",
            "## Ingestion Metrics",
            "",
            f"- **Total Chunks:** {summary['processed_chunks']}",
            f"- **New Embeddings Generated:** {summary['new_embeddings']}",
            f"- **Embeddings Reused (Cache/DB):** {summary['reused_embeddings']}",
            f"- **Failed Embeddings:** {summary['failed_embeddings']}",
            f"- **Skipped Chunks:** {summary['skipped_chunks']}",
            "",
            "> Embeddings are cached deterministically by `SHA256(content_hash + provider + model + dimension)`.",
        ]
        self.emb_report_md.write_text("\n".join(md_emb), encoding="utf-8")

    def _print_ingestion_summary(self, s: Dict[str, Any]) -> None:
        print()
        print("=" * 60)
        print("PHASE 4 COMPLETE: Knowledge Base & Embeddings Ingestion")
        print("=" * 60)
        print(f"Run ID              : {s['run_id']}")
        print(f"Total input chunks  : {s['total_input_chunks']}")
        print(f"Processed chunks    : {s['processed_chunks']}")
        print(f"New embeddings      : {s['new_embeddings']}")
        print(f"Reused embeddings   : {s['reused_embeddings']}")
        print(f"Failed embeddings   : {s['failed_embeddings']}")
        print(f"Skipped chunks      : {s['skipped_chunks']}")
        print(f"Elapsed time        : {s['elapsed_seconds']}s")
        print(f"Provider / Model    : {s['provider']} / {s['model']} ({s['dimension']}d)")
        print(f"Knowledge Base Dir  : {self.kb_data_path}")
        print(f"Status              : {s['status']}")
        print("=" * 60)
