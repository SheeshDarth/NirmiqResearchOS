import math
from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha1
from typing import NamedTuple


@dataclass(slots=True)
class BM25Hit:
    chunk_id: str
    score: float
    text: str
    document_id: str
    page_start: int | None
    page_end: int | None


class _CachedCorpus(NamedTuple):
    tokenized_docs: list[list[str]]
    term_frequencies: list[dict[str, int]]
    doc_freq: dict[str, int]
    avgdl: float


class BM25Index:
    """
    Lightweight in-process BM25 scorer.
    Reuses tokenized active corpora across repeated queries while keeping the
    cache key tied to chunk identity and searchable metadata.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75, max_cached_corpora: int = 4) -> None:
        self._k1 = k1
        self._b = b
        self._max_cached_corpora = max(1, max_cached_corpora)
        self._corpus_cache: OrderedDict[str, _CachedCorpus] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0
        self.last_cache_hit = False

    async def search(self, query: str, chunks: list[dict[str, object]], limit: int) -> list[BM25Hit]:
        results = await self.search_many(queries={"query": query}, chunks=chunks, limit=limit)
        return results.get("query", [])

    async def search_many(
        self,
        *,
        queries: dict[str, str],
        chunks: list[dict[str, object]],
        limit: int,
    ) -> dict[str, list[BM25Hit]]:
        """Score several evidence queries while tokenizing the corpus only once."""

        if not chunks or limit <= 0:
            self.last_cache_hit = False
            return {key: [] for key in queries}

        corpus = self._get_or_build_corpus(chunks)
        tokenized_docs = corpus.tokenized_docs
        term_frequencies = corpus.term_frequencies
        doc_freq = corpus.doc_freq
        avgdl = corpus.avgdl
        doc_count = len(tokenized_docs)

        results: dict[str, list[BM25Hit]] = {}
        for key, query in queries.items():
            query_tokens = self._tokenize(query)
            if not query_tokens:
                results[key] = []
                continue
            hits: list[BM25Hit] = []
            for idx, doc_tokens in enumerate(tokenized_docs):
                tf = term_frequencies[idx]
                doc_len = len(doc_tokens)
                score = 0.0
                for token in query_tokens:
                    if token not in tf:
                        continue
                    n_qi = doc_freq.get(token, 0)
                    idf = math.log(1 + (doc_count - n_qi + 0.5) / (n_qi + 0.5))
                    freq = tf[token]
                    denom = freq + self._k1 * (
                        1 - self._b + self._b * (doc_len / max(avgdl, 1e-9))
                    )
                    score += idf * ((freq * (self._k1 + 1)) / max(denom, 1e-9))
                if score <= 0:
                    continue
                row = chunks[idx]
                hits.append(
                    BM25Hit(
                        chunk_id=str(row["id"]),
                        score=score,
                        text=str(row["text"]),
                        document_id=str(row["document_id"]),
                        page_start=int(row["page_start"]) if row["page_start"] is not None else None,
                        page_end=int(row["page_end"]) if row["page_end"] is not None else None,
                    )
                )
            hits.sort(key=lambda item: item.score, reverse=True)
            results[key] = hits[:limit]
        return results

    def stats(self) -> dict[str, int]:
        return {
            "cached_corpora": len(self._corpus_cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_evictions": self._cache_evictions,
        }

    def clear(self) -> None:
        self._corpus_cache.clear()
        self.last_cache_hit = False

    def _get_or_build_corpus(self, chunks: list[dict[str, object]]) -> _CachedCorpus:
        key = self._corpus_cache_key(chunks)
        cached = self._corpus_cache.get(key)
        if cached is not None:
            self._corpus_cache.move_to_end(key)
            self._cache_hits += 1
            self.last_cache_hit = True
            return cached

        tokenized_docs = [self._tokenize(self._search_text(chunk)) for chunk in chunks]
        doc_count = len(tokenized_docs)
        avgdl = sum(len(doc) for doc in tokenized_docs) / max(doc_count, 1)
        doc_freq: dict[str, int] = {}
        term_frequencies: list[dict[str, int]] = []
        for doc_tokens in tokenized_docs:
            tf: dict[str, int] = {}
            for token in doc_tokens:
                tf[token] = tf.get(token, 0) + 1
            term_frequencies.append(tf)
            for token in set(doc_tokens):
                doc_freq[token] = doc_freq.get(token, 0) + 1
        corpus = _CachedCorpus(
            tokenized_docs=tokenized_docs,
            term_frequencies=term_frequencies,
            doc_freq=doc_freq,
            avgdl=avgdl,
        )
        self._corpus_cache[key] = corpus
        self._cache_misses += 1
        self.last_cache_hit = False
        while len(self._corpus_cache) > self._max_cached_corpora:
            self._corpus_cache.popitem(last=False)
            self._cache_evictions += 1
        return corpus

    def _corpus_cache_key(self, chunks: list[dict[str, object]]) -> str:
        digest = sha1()
        digest.update(f"bm25:{self._k1}:{self._b}:v2:{len(chunks)}".encode("utf-8"))
        for chunk in chunks:
            digest.update(str(chunk.get("id") or "").encode("utf-8", "ignore"))
            digest.update(b"\0")
            digest.update(str(chunk.get("document_id") or "").encode("utf-8", "ignore"))
            digest.update(b"\0")
            text_hash = chunk.get("chunk_hash")
            if text_hash:
                digest.update(str(text_hash).encode("utf-8", "ignore"))
            else:
                digest.update(sha1(self._search_text(chunk).encode("utf-8", "ignore")).hexdigest().encode())
            digest.update(b"\0")
            for key in ("heading", "section_path", "chunk_type", "key_terms_json"):
                digest.update(str(chunk.get(key) or "").encode("utf-8", "ignore"))
                digest.update(b"\0")
        return digest.hexdigest()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        lowered = text.lower()
        sanitized = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
        tokens: list[str] = []
        for token in sanitized.split():
            if not token:
                continue
            tokens.append(token)
            stem = BM25Index._light_stem(token)
            if stem != token:
                tokens.append(stem)
        return tokens

    @staticmethod
    def _search_text(chunk: dict[str, object]) -> str:
        metadata = " ".join(
            str(chunk.get(key) or "")
            for key in ("heading", "section_path", "chunk_type", "key_terms_json")
        )
        # Repeat compact academic metadata once so headings/definitions can beat generic body text.
        return f"{metadata} {metadata} {chunk.get('text') or ''}"

    @staticmethod
    def _light_stem(token: str) -> str:
        if len(token) > 5 and token.endswith("ing"):
            stem = token[:-3]
            if len(stem) > 3 and stem[-1] == stem[-2]:
                stem = stem[:-1]
            return stem
        if len(token) > 4 and token.endswith("ed"):
            return token[:-1] if token.endswith("eed") else token[:-2]
        if len(token) > 4 and token.endswith("e"):
            return token[:-1]
        if len(token) > 4 and token.endswith("s"):
            return token[:-1]
        return token
