"""共享存储抽象：local 实现读写与路径逃逸防护（worker 架构约定）。"""

from __future__ import annotations

import pytest
from worker.services.document_parser.storage.artifact_storage import (
    LocalArtifactStorage,
    get_artifact_storage,
)


def test_local_storage_roundtrip(tmp_path) -> None:
    storage = LocalArtifactStorage(root=str(tmp_path))
    key = storage.put_object("ns/doc/full.md", b"# hello")
    assert key == "ns/doc/full.md"
    assert storage.get_object("ns/doc/full.md") == b"# hello"


def test_local_storage_prefix_strip(tmp_path) -> None:
    storage = LocalArtifactStorage(root=str(tmp_path), prefix="local://")
    storage.put_object("local://a/b.txt", b"x")
    assert storage.get_object("a/b.txt") == b"x"


def test_local_storage_escapes_root(tmp_path) -> None:
    storage = LocalArtifactStorage(root=str(tmp_path))
    with pytest.raises(ValueError, match="escaped"):
        storage.put_object("../escape.txt", b"x")
    with pytest.raises(ValueError, match="escaped"):
        storage.get_object("/etc/passwd")


def test_delete_prefix(tmp_path) -> None:
    storage = LocalArtifactStorage(root=str(tmp_path))
    storage.put_object("ns/a.txt", b"1")
    storage.put_object("ns/sub/b.txt", b"2")
    storage.delete_prefix("ns")
    assert not (tmp_path / "ns").exists()
    with pytest.raises(FileNotFoundError):
        storage.get_object("ns/a.txt")
    storage.delete_prefix("ns")  # 幂等删除不报错


def test_get_artifact_storage_default_local(monkeypatch) -> None:
    monkeypatch.delenv("ARTIFACT_STORAGE", raising=False)
    monkeypatch.delenv("S3_BUCKET", raising=False)
    storage = get_artifact_storage()
    assert isinstance(storage, LocalArtifactStorage)
