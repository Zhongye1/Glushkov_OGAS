"""产物/文件存储抽象（设计文档 05 §4 + worker 架构约定）。

worker 契约：
- worker 是队列消费者，不对外开接口、不做用户鉴权；
- API 层把授权结果（tenant_id / namespace / s3_key）作为任务 payload 透传，
  worker 仅用它们做数据隔离（往哪个命名空间写产物）；
- 输入与产物一律按对象存储 key 传递，不依赖本地磁盘路径。

实现：LocalArtifactStorage（本地开发/测试）与 S3ArtifactStorage（惰性 boto3）。
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Protocol


class ArtifactStorage(Protocol):
    def get_object(self, key: str) -> bytes: ...

    def put_object(self, key: str, data: bytes) -> str: ...

    def delete_prefix(self, prefix: str) -> None: ...


@dataclass(frozen=True)
class LocalArtifactStorage:
    """本地实现：本地开发与测试用；生产走 S3ArtifactStorage。"""

    root: str
    prefix: str = "local://"

    def _resolve(self, key: str) -> str:
        raw = key[len(self.prefix):] if key.startswith(self.prefix) else key
        root = os.path.realpath(self.root)
        path = os.path.realpath(os.path.join(root, raw))
        if os.path.commonpath([root, path]) != root:
            raise ValueError(f"Storage key escaped root: {key}")
        return path

    def get_object(self, key: str) -> bytes:
        with open(self._resolve(key), "rb") as file:
            return file.read()

    def put_object(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as file:
            file.write(data)
        return key

    def delete_prefix(self, prefix: str) -> None:
        path = self._resolve(prefix)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.exists(path):
            os.remove(path)


@dataclass(frozen=True)
class S3ArtifactStorage:
    """S3 实现：key 即对象键，惰性 boto3。"""

    bucket: str
    prefix: str = ""

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def get_object(self, key: str) -> bytes:
        import boto3  # 惰性导入

        body = boto3.client("s3").get_object(
            Bucket=self.bucket, Key=self._full_key(key)
        )["Body"]
        return body.read()

    def put_object(self, key: str, data: bytes) -> str:
        import boto3  # 惰性导入

        boto3.client("s3").put_object(
            Bucket=self.bucket, Key=self._full_key(key), Body=data
        )
        return key

    def delete_prefix(self, prefix: str) -> None:
        import boto3  # 惰性导入

        client = boto3.client("s3")
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self._full_key(prefix)):
            objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if objects:
                client.delete_objects(Bucket=self.bucket, Delete={"Objects": objects})


def get_artifact_storage() -> ArtifactStorage:
    """按环境变量选择存储实现：ARTIFACT_STORAGE=local|s3。"""
    kind = os.getenv("ARTIFACT_STORAGE", "local").lower()
    if kind == "s3":
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            raise RuntimeError("ARTIFACT_STORAGE=s3 requires S3_BUCKET")
        return S3ArtifactStorage(
            bucket=bucket,
            prefix=os.getenv("S3_PREFIX", ""),
        )
    return LocalArtifactStorage(
        root=os.getenv("ARTIFACT_STORAGE_LOCAL_ROOT", "/tmp/parsing-artifacts")
    )
