import pytest

import services.llm.embedder as embedder
from services.llm.embedder import EmbedderService, EmbeddingError


class BrokenModel:
    def embed(self, texts):
        raise RuntimeError("backend down")


class FakeModel:
    def __init__(self, dim=384):
        self.dim = dim

    def embed(self, texts):
        for text in texts:
            yield [3.0] + [0.0] * (self.dim - 1)


@pytest.fixture(autouse=True)
def reset_model(monkeypatch):
    monkeypatch.setattr(embedder, "_model", None)


def test_failure_raises_instead_of_zero_vector(monkeypatch):
    monkeypatch.setattr(embedder, "_model", BrokenModel())
    service = EmbedderService()
    with pytest.raises(EmbeddingError):
        service.embed_text("hello")
    with pytest.raises(EmbeddingError):
        service.embed_texts(["a", "b"])


def test_vectors_are_normalised(monkeypatch):
    monkeypatch.setattr(embedder, "_model", FakeModel())
    vector = EmbedderService().embed_text("hello")
    assert len(vector) == 384
    assert vector[0] == pytest.approx(1.0)


def test_wrong_dimension_is_an_error(monkeypatch):
    monkeypatch.setattr(embedder, "_model", FakeModel(dim=10))
    with pytest.raises(EmbeddingError):
        EmbedderService().embed_text("hello")


def test_empty_input():
    service = EmbedderService()
    with pytest.raises(ValueError):
        service.embed_text("")
    assert service.embed_texts([]) == []
