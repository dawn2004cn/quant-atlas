"""Local classified knowledge base store (JSONL under instance/knowledge_base).

Categories: yanbao / news / financial / industry_chain / corpus.
Designed for AI tools: search + compact prompt packs, no vector DB required.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

CATEGORIES = ("yanbao", "news", "financial", "industry_chain", "corpus")

_CATEGORY_LABELS = {
    "yanbao": "研报",
    "news": "新闻",
    "financial": "财报",
    "industry_chain": "产业链",
    "corpus": "基础知识",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _tokenize(text: str) -> set[str]:
    parts = re.split(r"[\s,，。；;、/|+\-_:：]+", (text or "").lower())
    return {p for p in parts if len(p) >= 2}


def _score(query: str, *fields: str) -> float:
    q = (query or "").strip().lower()
    blob = " ".join(str(f or "") for f in fields).lower()
    if not q:
        return 1.0
    score = 0.0
    if q in blob:
        score += 5.0
    for tok in _tokenize(q):
        if tok in blob:
            score += 1.0
    return score


class KnowledgeLocalStore:
    """Thread-safe JSONL store with upsert-by-id and category indexes."""

    def __init__(self, root: Path | str | None = None) -> None:
        if root is None:
            from app.config import INSTANCE_DIR

            root = Path(INSTANCE_DIR) / "knowledge_base"
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._docs_path = self._root / "documents.jsonl"
        self._lock = threading.Lock()
        self._cache: dict[str, dict[str, Any]] | None = None

    @property
    def root(self) -> Path:
        return self._root

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._cache is not None:
            return self._cache
        docs: dict[str, dict[str, Any]] = {}
        if self._docs_path.is_file():
            try:
                with open(self._docs_path, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        doc_id = str(row.get("id") or "").strip()
                        if doc_id:
                            docs[doc_id] = row
            except OSError as exc:
                logger.warning("knowledge store load failed: %s", exc, exc_info=True)
        self._cache = docs
        return docs

    def _persist(self, docs: dict[str, dict[str, Any]]) -> None:
        tmp = self._docs_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            for row in docs.values():
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        tmp.replace(self._docs_path)
        # category sidecars for AI / ops browsing
        by_cat: dict[str, list[dict[str, Any]]] = {c: [] for c in CATEGORIES}
        for row in docs.values():
            cat = str(row.get("category") or "")
            if cat in by_cat:
                by_cat[cat].append(row)
        cat_dir = self._root / "by_category"
        cat_dir.mkdir(parents=True, exist_ok=True)
        for cat, rows in by_cat.items():
            path = cat_dir / f"{cat}.jsonl"
            with open(path, "w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def upsert(self, doc: dict[str, Any]) -> dict[str, Any]:
        doc_id = str(doc.get("id") or "").strip()
        if not doc_id:
            raise ValueError("document id required")
        category = str(doc.get("category") or "").strip()
        if category not in CATEGORIES:
            raise ValueError(f"invalid category: {category}")
        row = {
            "id": doc_id,
            "category": category,
            "title": str(doc.get("title") or "")[:512],
            "content": str(doc.get("content") or "")[:4000],
            "symbol": (str(doc.get("symbol") or "").strip().upper() or None),
            "tags": list(doc.get("tags") or [])[:24],
            "source": str(doc.get("source") or "")[:128],
            "url": str(doc.get("url") or "")[:1024] or None,
            "published_at": str(doc.get("published_at") or "")[:64] or None,
            "meta": dict(doc.get("meta") or {}),
            "updated_at": _utc_now(),
        }
        with self._lock:
            docs = self._load()
            docs[doc_id] = row
            self._persist(docs)
            self._cache = docs
        return row

    def upsert_many(self, docs_in: list[dict[str, Any]]) -> int:
        n = 0
        with self._lock:
            docs = self._load()
            for doc in docs_in:
                doc_id = str(doc.get("id") or "").strip()
                category = str(doc.get("category") or "").strip()
                if not doc_id or category not in CATEGORIES:
                    continue
                docs[doc_id] = {
                    "id": doc_id,
                    "category": category,
                    "title": str(doc.get("title") or "")[:512],
                    "content": str(doc.get("content") or "")[:4000],
                    "symbol": (str(doc.get("symbol") or "").strip().upper() or None),
                    "tags": list(doc.get("tags") or [])[:24],
                    "source": str(doc.get("source") or "")[:128],
                    "url": str(doc.get("url") or "")[:1024] or None,
                    "published_at": str(doc.get("published_at") or "")[:64] or None,
                    "meta": dict(doc.get("meta") or {}),
                    "updated_at": _utc_now(),
                }
                n += 1
            if n:
                self._persist(docs)
                self._cache = docs
        return n

    def list_docs(
        self,
        *,
        category: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self._lock:
            docs = list(self._load().values())
        sym = (symbol or "").strip().upper() or None
        if category:
            docs = [d for d in docs if d.get("category") == category]
        if sym:
            docs = [d for d in docs if (d.get("symbol") or "") == sym or sym in str(d.get("title") or "")]
        docs.sort(key=lambda d: str(d.get("updated_at") or ""), reverse=True)
        return docs[: max(1, min(int(limit), 200))]

    def search(
        self,
        query: str = "",
        *,
        categories: list[str] | None = None,
        symbol: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        with self._lock:
            docs = list(self._load().values())
        wanted = set(categories or CATEGORIES)
        sym = (symbol or "").strip().upper() or None
        scored: list[tuple[float, dict[str, Any]]] = []
        for d in docs:
            if d.get("category") not in wanted:
                continue
            if sym and (d.get("symbol") or "") != sym and sym not in str(d.get("title") or ""):
                # soft: still allow title/content match without symbol filter miss
                if query and _score(query, d.get("title", ""), d.get("content", ""), " ".join(d.get("tags") or "")) <= 0:
                    continue
                if not query:
                    continue
            sc = _score(
                query,
                d.get("title", ""),
                d.get("content", ""),
                " ".join(d.get("tags") or []),
                d.get("symbol") or "",
                d.get("category") or "",
            )
            if sym and ((d.get("symbol") or "") == sym or sym in str(d.get("title") or "")):
                sc += 2.0
            if query and sc <= 0:
                continue
            scored.append((sc, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for sc, d in scored[: max(1, min(int(limit), 80))]:
            item = dict(d)
            item["score"] = sc
            out.append(item)
        return out

    def stats(self) -> dict[str, Any]:
        with self._lock:
            docs = list(self._load().values())
        by_category: dict[str, int] = {c: 0 for c in CATEGORIES}
        for d in docs:
            cat = str(d.get("category") or "")
            if cat in by_category:
                by_category[cat] += 1
        return {
            "root": str(self._root),
            "total": len(docs),
            "by_category": by_category,
            "labels": dict(_CATEGORY_LABELS),
        }

    def build_ai_pack(
        self,
        *,
        symbol: str | None = None,
        query: str = "",
        limit: int = 24,
    ) -> dict[str, Any]:
        """Compact classified pack for LLM context injection."""
        items = self.search(query, symbol=symbol, limit=limit)
        by_category: dict[str, list[dict[str, Any]]] = {}
        for it in items:
            cat = str(it.get("category") or "corpus")
            by_category.setdefault(cat, []).append(
                {
                    "id": it.get("id"),
                    "title": it.get("title"),
                    "content": (it.get("content") or "")[:600],
                    "symbol": it.get("symbol"),
                    "published_at": it.get("published_at"),
                    "source": it.get("source"),
                    "tags": it.get("tags") or [],
                }
            )
        lines = [
            f"# Quant Atlas 本地知识包 symbol={symbol or '-'} query={query or '-'}",
            f"docs={len(items)} updated={_utc_now()}",
            "",
        ]
        for cat in CATEGORIES:
            rows = by_category.get(cat) or []
            if not rows:
                continue
            label = _CATEGORY_LABELS.get(cat, cat)
            lines.append(f"### {label} ({cat})")
            for r in rows[:8]:
                lines.append(f"- {r.get('title')}: {(r.get('content') or '')[:220]}")
            lines.append("")
        return {
            "symbol": (symbol or "").strip().upper() or None,
            "query": query,
            "count": len(items),
            "by_category": by_category,
            "prompt_block": "\n".join(lines).strip(),
            "generated_at": _utc_now(),
        }


__all__ = ["KnowledgeLocalStore", "CATEGORIES"]
