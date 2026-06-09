"""Text embeddings.

NOTE: This is an intentionally lightweight, dependency-free STUB. A real
deployment would swap in sentence-transformers or an embeddings API. The
hashing-based vector here is deterministic and good enough for similarity-style
demos without pulling in heavy ML dependencies.
"""
import hashlib
import math

DIM = 64


def embed(text: str):
    """Return a deterministic ``DIM``-dimensional unit vector for ``text``."""
    text = (text or "").lower()
    vec = [0.0] * DIM
    for token in text.split():
        h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        idx = h % DIM
        sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_similarity(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))
