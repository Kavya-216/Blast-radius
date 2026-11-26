import math
import re
from collections import Counter


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
QUERY_STOP_WORDS = {
    "a", "an", "and", "are", "about", "can", "do", "does", "for", "how",
    "i", "in", "is", "it", "me", "of", "on", "or", "the", "this", "to",
    "what", "which", "who", "why", "with", "you",
}


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def focus_query(query: str) -> str:
    tokens = tokenize(query)
    if "anything" in tokens:
        tokens = [token for token in tokens if token not in {"rag", "anything"}]
    focused = [token for token in tokens if token not in QUERY_STOP_WORDS]
    return " ".join(focused) or query


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: list[list[str]] = []
        self.term_frequencies: list[Counter] = []
        self.document_frequencies: Counter = Counter()
        self.average_length = 0.0

    def fit(self, documents: list[str]) -> "BM25":
        self.documents = [tokenize(document) for document in documents]
        self.term_frequencies = [Counter(document) for document in self.documents]
        self.document_frequencies = Counter()
        for frequencies in self.term_frequencies:
            self.document_frequencies.update(frequencies.keys())
        self.average_length = (
            sum(len(document) for document in self.documents) / len(self.documents)
            if self.documents else 0.0
        )
        return self

    def search(self, query: str, limit: int = 10) -> list[tuple[int, float]]:
        query_terms = tokenize(query)
        scored: list[tuple[int, float]] = []
        document_count = len(self.documents)
        for index, frequencies in enumerate(self.term_frequencies):
            score = 0.0
            length = len(self.documents[index])
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                df = self.document_frequencies.get(term, 0)
                idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length / max(self.average_length, 1.0)
                )
                score += idf * frequency * (self.k1 + 1) / denominator
            if score > 0:
                scored.append((index, score))
        return sorted(scored, key=lambda item: (-item[1], item[0]))[:limit]
