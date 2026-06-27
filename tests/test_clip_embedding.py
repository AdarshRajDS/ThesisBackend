import numpy as np

from src.multimodal.clip_embedding import CLIPEmbedding, _clip_safe_text


class _FakeModel:
    def encode(self, texts, convert_to_numpy=True):
        text = texts[0]
        if len(text.split()) > 77:
            raise RuntimeError("The size of tensor a (84) must match the size of tensor b (77)")
        return np.array([[1.0, 2.0, 3.0]])


class _VeryStrictFakeModel:
    def encode(self, texts, convert_to_numpy=True):
        text = texts[0]
        if len(text.split()) > 4:
            raise RuntimeError("The size of tensor a (84) must match the size of tensor b (77)")
        return np.array([[3.0, 2.0, 1.0]])


def test_clip_safe_text_limits_words_and_chars():
    long_text = "wort " * 200
    out = _clip_safe_text(long_text)
    assert len(out.split()) <= 40
    assert len(out) <= 220


def test_embed_text_retries_with_shortened_query():
    emb = CLIPEmbedding.__new__(CLIPEmbedding)
    emb.model = _FakeModel()

    long_query = "muskel " * 120
    vec = emb.embed_text([long_query])

    assert vec.shape == (1, 3)


def test_embed_text_multiple_retries_until_safe():
    emb = CLIPEmbedding.__new__(CLIPEmbedding)
    emb.model = _VeryStrictFakeModel()

    long_query = "muskel " * 120
    vec = emb.embed_text([long_query])

    assert vec.shape == (1, 3)
