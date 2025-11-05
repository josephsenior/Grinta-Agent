from __future__ import annotations

"Lightweight in-process memory index bootstrap.\n\nThis is a minimal, dependency-free retrieval layer to:\n  * Persist step artifacts (textual fields) + rationale\n  * Provide naive semantic search via hashed token overlap and cosine over bag-of-words vectors\n  * Support future replacement with a vector DB (FAISS, SQLite extension, etc.)\n\nDesign goals:\n  - Keep writes cheap (append-only JSONL + in-memory index during run)\n  - Provide deterministic scoring for testability\n  - Avoid external deps for initial bootstrap\n"
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile("[A-Za-z0-9_]{2,}")


@dataclass
class MemoryRecord:
    step_id: str
    role: str
    artifact_hash: str | None
    rationale: str | None
    content_excerpt: str
    tokens: dict[str, int]
    __test__ = False


class MemoryIndex:

    def __init__(self, run_id: str, base_dir: Path | None = None, max_records: int | None = 500) -> None:
        self.run_id = run_id
        self.base_dir = base_dir or Path.home() / ".openhands" / "memory"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._records: list[MemoryRecord] = []
        self._df: dict[str, int] = {}
        self._jsonl_path = self.base_dir / f"memory_{run_id}.jsonl"
        self._max_records = max_records
        self._unique_term_threshold = 2000
        self._compaction_target = int((self._max_records or 500) * 0.75)

    def _tokenize(self, text: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for m in TOKEN_RE.finditer(text.lower()):
            tok = m.group(0)
            counts[tok] = counts.get(tok, 0) + 1
        return counts

    def _tfidf_vector(self, tokens: dict[str, int]) -> dict[str, float]:
        total_docs = max(len(self._records), 1)
        return {t: freq * math.log((total_docs + 1) / (1 + self._df.get(t, 0))) for t, freq in tokens.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        common = set(a.keys()) & set(b.keys())
        num = sum(a[t] * b[t] for t in common)
        denom = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
        return 0.0 if denom == 0 else num / denom

    def add(self, step_id: str, role: str, artifact_hash: str | None, rationale: str | None, content: str) -> None:
        """Add a memory record to the index.

        Args:
            step_id: Step identifier
            role: Role name
            artifact_hash: Optional artifact hash
            rationale: Optional rationale
            content: Content to index
        """
        excerpt = content[:2000]
        tokens = self._tokenize((rationale or "") + "\n" + excerpt)

        self._update_document_frequency(tokens)
        rec = MemoryRecord(step_id, role, artifact_hash, rationale, excerpt, tokens)
        self._records.append(rec)

        self._handle_capacity_limits()
        self._persist_record(step_id, role, artifact_hash, rationale, excerpt)

    def _update_document_frequency(self, tokens: dict) -> None:
        """Update document frequency for tokens.

        Args:
            tokens: Token frequency dictionary
        """
        for t in tokens:
            self._df[t] = self._df.get(t, 0) + 1

    def _handle_capacity_limits(self) -> None:
        """Handle capacity limits by compacting or removing old records."""
        should_compact = (self._max_records and len(self._records) > self._max_records) or len(
            self._df,
        ) > self._unique_term_threshold

        if should_compact:
            self._compact()

        # Remove oldest if still over limit
        if self._max_records and len(self._records) > self._max_records:
            self._records.pop(0)
            self._rebuild_document_frequency()

    def _rebuild_document_frequency(self) -> None:
        """Rebuild document frequency from current records."""
        self._df.clear()
        for r in self._records:
            for tok in r.tokens:
                self._df[tok] = self._df.get(tok, 0) + 1

    def _persist_record(
        self, step_id: str, role: str, artifact_hash: str | None, rationale: str | None, excerpt: str,
    ) -> None:
        """Persist record to JSONL file.

        Args:
            step_id: Step identifier
            role: Role name
            artifact_hash: Optional artifact hash
            rationale: Optional rationale
            excerpt: Content excerpt
        """
        try:
            with self._jsonl_path.open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "step_id": step_id,
                            "role": role,
                            "artifact_hash": artifact_hash,
                            "rationale": rationale,
                            "excerpt": excerpt,
                        },
                    )
                    + "\n",
                )
        except Exception:
            pass

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        q_tokens = self._tokenize(query)
        q_vec = self._tfidf_vector(q_tokens)
        scored: list[tuple[float, MemoryRecord]] = []
        for rec in self._records:
            rec_vec = self._tfidf_vector(rec.tokens)
            score = self._cosine(q_vec, rec_vec)
            if score > 0:
                scored.append((score, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "step_id": rec.step_id,
                "role": rec.role,
                "score": round(score, 4),
                "artifact_hash": rec.artifact_hash,
                "rationale": rec.rationale,
                "excerpt": rec.content_excerpt,
            }
            for score, rec in scored[:k]
        ]

    def _score_record(self, rec: MemoryRecord, q_vec: dict[str, float]) -> float:
        """Compute a lightweight score combining semantic match (cosine) and recency bias.

        Recency is approximated by position: newer records are later in the list.
        """
        rec_vec = self._tfidf_vector(rec.tokens)
        sem = self._cosine(q_vec, rec_vec)
        idx = self._records.index(rec) if rec in self._records else 0
        recency = 1.0 - idx / max(len(self._records), 1) * 0.5
        return sem * 0.8 + recency * 0.2

    def _compact(self) -> None:
        """Run a simple compaction pass to remove low-value records.

        Strategy:
        - Score each record by token overlap with the whole corpus (novelty) and recency.
        - Drop the oldest/lowest-scoring records until under target size.
        """
        if not self._records or self._compaction_target <= 0:
            return

        q_vec = self._build_compaction_query_vector()
        scored = self._score_all_records(q_vec)
        self._keep_top_records(scored)
        self._rebuild_document_frequency()

    def _build_compaction_query_vector(self) -> dict[str, float]:
        """Build query vector from top terms for compaction.

        Returns:
            TF-IDF vector for top terms
        """
        top_terms = sorted(self._df.items(), key=lambda x: x[1], reverse=True)[:50]
        pseudo_q = {t: 1 for t, _ in top_terms}
        return self._tfidf_vector(pseudo_q)

    def _score_all_records(self, q_vec: dict[str, float]) -> list[tuple]:
        """Score all records for compaction.

        Args:
            q_vec: Query vector for scoring

        Returns:
            List of (score, index, record) tuples sorted by score
        """
        scored = [(self._score_record(r, q_vec), i, r) for i, r in enumerate(self._records)]
        scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        return scored

    def _keep_top_records(self, scored: list[tuple]) -> None:
        """Keep only top-scoring records up to target.

        Args:
            scored: Sorted list of (score, index, record) tuples
        """
        kept = [r for _, _, r in scored[: self._compaction_target]]
        kept_ids = {id(r) for r in kept}
        self._records = [r for r in self._records if id(r) in kept_ids]

    def stats(self) -> dict[str, Any]:
        return {"records": len(self._records), "unique_terms": len(self._df)}
