import pytest
from unittest.mock import patch

from app.rag.retriever import store_chunks, search_chunks

# 1536 维的假向量（和 text-embedding-3-small 输出维度一致）
FAKE_DIM = 1536


def fake_vector(seed: float = 0.1) -> list[float]:
    return [seed] * FAKE_DIM


def fake_embed(chunks):
    """替换真实 OpenAI 调用，给每个 chunk 分配一个假向量。"""
    return [{**chunk, "embedding": fake_vector()} for chunk in chunks]


# ---------- store_chunks ----------

def test_store_chunks_does_not_raise():
    """存一个 chunk 不抛异常。"""
    chunks = [
        {
            "filename": "foo.py",
            "content": "def hello(): pass",
            "embedding": fake_vector(),
        }
    ]
    store_chunks(chunks)  # 不应报错


def test_store_chunks_empty_list():
    """空列表也能正常执行（建空集合）。"""
    store_chunks([])


# ---------- search_chunks ----------

def test_search_returns_stored_chunk():
    """存一个 chunk，搜出来的结果里要有它。"""
    chunks = [
        {
            "filename": "bar.py",
            "content": "def bar(): return 42",
            "embedding": fake_vector(0.5),
        }
    ]
    store_chunks(chunks)

    with patch("app.rag.retriever.embed_chunks", side_effect=fake_embed):
        results = search_chunks("bar function")

    assert len(results) >= 1
    assert results[0]["filename"] == "bar.py"


def test_search_result_has_required_keys():
    """每条搜索结果都包含 filename、content、score。"""
    chunks = [
        {
            "filename": "utils.py",
            "content": "some utility code",
            "embedding": fake_vector(),
        }
    ]
    store_chunks(chunks)

    with patch("app.rag.retriever.embed_chunks", side_effect=fake_embed):
        results = search_chunks("utility")

    assert "filename" in results[0]
    assert "content" in results[0]
    assert "score" in results[0]


def test_search_respects_top_k():
    """top_k 参数限制返回条数。"""
    chunks = [
        {
            "filename": f"file{i}.py",
            "content": f"content {i}",
            "embedding": fake_vector(i * 0.01),
        }
        for i in range(10)
    ]
    store_chunks(chunks)

    with patch("app.rag.retriever.embed_chunks", side_effect=fake_embed):
        results = search_chunks("query", top_k=3)

    assert len(results) <= 3
