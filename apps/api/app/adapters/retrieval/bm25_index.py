import math
from dataclasses import dataclass


@dataclass(slots=True)
class BM25Hit:
    chunk_id: str
    score: float
    text: str
    document_id: str
    page_start: int | None
    page_end: int | None


class BM25Index:
    """
    Lightweight in-process BM25 scorer.
    Rebuilds per query from active chunks to keep Phase 1 simple and robust.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b

    async def search(self, query: str, chunks: list[dict[str, object]], limit: int) -> list[BM25Hit]:
        if not query.strip() or not chunks:
            return []

        tokenized_docs: list[list[str]] = [self._tokenize(str(chunk["text"])) for chunk in chunks]
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        doc_count = len(tokenized_docs)
        avgdl = sum(len(doc) for doc in tokenized_docs) / max(doc_count, 1)
        doc_freq: dict[str, int] = {}
        for doc_tokens in tokenized_docs:
            for token in set(doc_tokens):
                doc_freq[token] = doc_freq.get(token, 0) + 1

        hits: list[BM25Hit] = []
        for idx, doc_tokens in enumerate(tokenized_docs):
            tf: dict[str, int] = {}
            for token in doc_tokens:
                tf[token] = tf.get(token, 0) + 1
            doc_len = len(doc_tokens)
            score = 0.0
            for token in query_tokens:
                if token not in tf:
                    continue
                n_qi = doc_freq.get(token, 0)
                idf = math.log(1 + (doc_count - n_qi + 0.5) / (n_qi + 0.5))
                freq = tf[token]
                denom = freq + self._k1 * (1 - self._b + self._b * (doc_len / max(avgdl, 1e-9)))
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
        return hits[:limit]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        lowered = text.lower()
        sanitized = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
        return [token for token in sanitized.split() if token]
