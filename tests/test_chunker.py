import pytest
from app.rag.chunker import chunk_pr_files


def test_short_file_produces_one_chunk():
    """不足 30 行的文件只产生一个 chunk。"""
    files = [{"filename": "foo.py", "patch": "line1\nline2\nline3"}]
    chunks = chunk_pr_files(files)
    assert len(chunks) == 1
    assert chunks[0]["filename"] == "foo.py"


def test_long_file_produces_multiple_chunks():
    """61 行应该产生 3 个 chunk（30 + 30 + 1）。"""
    patch = "\n".join(f"line{i}" for i in range(61))
    files = [{"filename": "big.py", "patch": patch}]
    chunks = chunk_pr_files(files)
    assert len(chunks) == 3


def test_exactly_30_lines_produces_one_chunk():
    """恰好 30 行只产生 1 个 chunk（边界条件）。"""
    patch = "\n".join(f"line{i}" for i in range(30))
    files = [{"filename": "exact.py", "patch": patch}]
    chunks = chunk_pr_files(files)
    assert len(chunks) == 1


def test_empty_patch_skipped():
    """空字符串 patch 不产生任何 chunk。"""
    files = [{"filename": "empty.py", "patch": ""}]
    chunks = chunk_pr_files(files)
    assert len(chunks) == 0


def test_none_patch_skipped():
    """patch 为 None 的文件跳过，不报错。"""
    files = [{"filename": "none.py", "patch": None}]
    chunks = chunk_pr_files(files)
    assert len(chunks) == 0


def test_chunk_preserves_filename():
    """每个 chunk 都带有原文件名。"""
    files = [{"filename": "app/main.py", "patch": "some code\nmore code"}]
    chunks = chunk_pr_files(files)
    assert chunks[0]["filename"] == "app/main.py"


def test_multiple_files_each_chunked():
    """多个文件分别被切块，filename 互不干扰。"""
    files = [
        {"filename": "a.py", "patch": "code a"},
        {"filename": "b.py", "patch": "code b"},
    ]
    chunks = chunk_pr_files(files)
    assert len(chunks) == 2
    assert chunks[0]["filename"] == "a.py"
    assert chunks[1]["filename"] == "b.py"


def test_chunk_content_matches_patch():
    """chunk 的 content 包含原始 patch 内容。"""
    files = [{"filename": "foo.py", "patch": "+def hello():\n+    pass"}]
    chunks = chunk_pr_files(files)
    assert "+def hello():" in chunks[0]["content"]
