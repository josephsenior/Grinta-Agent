"""Lightweight in-process memory index for MetaSOP step artifacts."""

from __future__ import annotations
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile("[A-Za-z0-9_]{2,}")


@dataclass
class MemoryRecord:
    """Normalized memory entry persisted and searched by MemoryIndex."""

    step_id: str
    role: str
    artifact_hash: str | None
    rationale: str | None
    content_excerpt: str
    tokens: dict[str, int]
    __test__ = False


class MemoryIndex:
    """Lightweight TF-IDF memory store with append-only persistence."""

    def __init__(
        self, run_id: str, base_dir: Path | None = None, max_records: int | None = 500
    ) -> None:
        """Initialize in-process memory index for step artifacts and semantic search.

        Args:
            run_id: Unique identifier for this orchestration run
            base_dir: Base directory for JSONL persistence. Defaults to ~/.Forge/memory
            max_records: Maximum memory records to keep in-memory. Defaults to 500

        Returns:
            None

        Side Effects:
            - Creates base_dir if not exists
            - Initializes empty in-memory index and document frequency table
            - Sets up JSONL file path for persistence

        Notes:
            - Dependency-free implementation using token overlap + TF-IDF cosine similarity
            - Records are compacted when exceeding max_records or unique term threshold
            - All writes are append-only to JSONL for replay/recovery

        Example:
            >>> index = MemoryIndex("run_001")
            >>> index.add("step_1", "coder", None, "Fixed bug", "def fix(): pass")
            >>> index._records[0].step_id
            'step_1'

        """
        self.run_id = run_id
        self.base_dir = base_dir or Path.home() / ".Forge" / "memory"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._records: list[MemoryRecord] = []
        self._df: dict[str, int] = {}
        self._jsonl_path = self.base_dir / f"memory_{run_id}.jsonl"
        self._max_records = max_records
        self._unique_term_threshold = 2000
        self._compaction_target = int((self._max_records or 500) * 0.75)

    def _tokenize(self, text: str) -> dict[str, int]:
        """Tokenize text into word tokens and count frequencies.

        Uses regex to extract alphanumeric tokens of length >= 2 characters.
        Converts to lowercase for case-insensitive matching.

        Args:
            text: Input text to tokenize

        Returns:
            dict: Token -> frequency count mapping

        Side Effects:
            None - Pure function

        Notes:
            - Regex pattern: [A-Za-z0-9_]{2,} (2+ char words, underscores allowed)
            - Used for both content and rationale tokenization
            - Case normalization ensures deterministic token sets

        Example:
            >>> index = MemoryIndex("run_1")
            >>> index._tokenize("Hello world_123 x")
            {'hello': 1, 'world_123': 1}  # 'x' filtered (< 2 chars)

        """
        counts: dict[str, int] = {}
        for m in TOKEN_RE.finditer(text.lower()):
            tok = m.group(0)
            counts[tok] = counts.get(tok, 0) + 1
        return counts

    def _tfidf_vector(self, tokens: dict[str, int]) -> dict[str, float]:
        """Compute TF-IDF vector from token counts.

        Converts token frequencies to TF-IDF scores using document frequency table.
        TF-IDF = frequency * log((total_docs + 1) / (1 + doc_freq))

        Args:
            tokens: Token frequency dictionary from _tokenize

        Returns:
            dict: Token -> TF-IDF score mapping

        Side Effects:
            None - Reads _df and _records, no modifications

        Notes:
            - Laplace smoothing prevents division by zero
            - Higher scores for rare tokens (information-rich)
            - Used for cosine similarity ranking in search

        Example:
            >>> index = MemoryIndex("run_1")
            >>> index.add("s1", "role", None, None, "apple banana apple")
            >>> vector = index._tfidf_vector({"apple": 2, "banana": 1})
            >>> 0 < vector["apple"] < vector["banana"]  # apple is less rare
            False  # apple is MORE common so lower TF-IDF

        """
        total_docs = max(len(self._records), 1)
        return {
            t: freq * math.log((total_docs + 1) / (1 + self._df.get(t, 0)))
            for t, freq in tokens.items()
        }

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        """Compute cosine similarity between two TF-IDF vectors.

        Args:
            a: First TF-IDF vector (token -> score)
            b: Second TF-IDF vector (token -> score)

        Returns:
            float: Cosine similarity in range [0.0, 1.0]

        Side Effects:
            None - Pure function

        Notes:
            - Formula: dot(a,b) / (||a|| * ||b||)
            - Returns 0.0 if either vector is empty or magnitude is 0
            - Ranges from 0 (orthogonal) to 1 (identical direction)

        Example:
            >>> MemoryIndex._cosine({"a": 1.0, "b": 1.0}, {"a": 1.0, "b": 1.0})
            1.0  # Identical vectors
            >>> MemoryIndex._cosine({"a": 1.0}, {"b": 1.0})
            0.0  # No common tokens

        """
        if not a or not b:
            return 0.0
        common = set(a.keys()) & set(b.keys())
        num = sum(a[t] * b[t] for t in common)
        denom = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(
            sum(v * v for v in b.values())
        )
        return 0.0 if denom == 0 else num / denom

    def add(
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        content: str,
    ) -> None:
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
        should_compact = (
            self._max_records and len(self._records) > self._max_records
        ) or len(
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
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        excerpt: str,
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
        """Return top-k records matching query using cosine similarity."""
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
        scored = [
            (self._score_record(r, q_vec), i, r) for i, r in enumerate(self._records)
        ]
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
        """Expose simple diagnostics about record count and vocabulary size."""
        return {"records": len(self._records), "unique_terms": len(self._df)}
