"""Tests for text embeddings and semantic product search."""

from __future__ import annotations

from apps.ai_engine.ml.algorithms import text_embedding


ITEM_IDS = ["i0", "i1", "i2", "i3"]
DOCUMENTS = [
    "Acme Wireless Headphones bluetooth audio electronics",
    "Northwind Hardcover Cookbook recipes kitchen books",
    "Globex Running Shoes lightweight sports footwear",
    "Initech Smartphone 5G camera electronics mobile",
]


def test_factory_defaults_to_tfidf():
    """The default backend is the deterministic TF-IDF model."""
    model = text_embedding.build_embedding_model("tfidf")
    assert model.backend == "tfidf"


def test_factory_falls_back_when_heavy_backend_unavailable():
    """Requesting an unavailable heavy backend falls back to TF-IDF."""
    if text_embedding.sentence_transformers_available() and text_embedding.torch_available():
        return
    model = text_embedding.build_embedding_model("sentence-transformers")
    assert model.backend == "tfidf"


def test_search_ranks_relevant_item_first():
    """A query about electronics ranks the electronics items highest."""
    model = text_embedding.TfidfEmbeddingModel().fit(ITEM_IDS, DOCUMENTS)
    results = model.search("wireless bluetooth headphones", k=2)
    assert results
    assert results[0][0] == "i0"


def test_search_results_are_sorted_descending():
    """Similarity scores are returned in descending order."""
    model = text_embedding.TfidfEmbeddingModel().fit(ITEM_IDS, DOCUMENTS)
    scores = [score for _, score in model.search("sports running shoes", k=4)]
    assert scores == sorted(scores, reverse=True)


def test_search_excludes_zero_similarity():
    """Items with no token overlap are not returned."""
    model = text_embedding.TfidfEmbeddingModel().fit(ITEM_IDS, DOCUMENTS)
    results = model.search("quantum telescope", k=4)
    assert results == []


def test_unfitted_search_raises():
    """Searching before fit is a clear error."""
    model = text_embedding.TfidfEmbeddingModel()
    try:
        model.search("anything")
    except RuntimeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Expected RuntimeError")


def test_encode_returns_one_vector_per_text():
    """``encode`` returns a row per input text."""
    model = text_embedding.TfidfEmbeddingModel().fit(ITEM_IDS, DOCUMENTS)
    vectors = model.encode(["electronics", "cookbook"])
    assert vectors.shape[0] == 2
