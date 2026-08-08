"""解析 worker 的 Celery 应用入口（队列消费者，无 HTTP、无鉴权）。

worker 架构约定：
- worker 是队列消费者，不对外开接口、不做用户鉴权；auth 收敛在 API 入口层；
- API 层鉴权后把授权结果（tenant_id / namespace / s3_key）透传进任务消息，
  worker 只用它们做数据隔离；
- 输入与产物经 ArtifactStorage 的对象存储 key 传递，不依赖本地磁盘路径。

独立进程启动（worker 镜像）：
    python -m worker.services.document_parser.worker_app
或等价地：
    celery -A worker.services.document_parser.worker_app:celery_app worker -Q parsing

配置（环境变量）：
    CELERY_BROKER_URL         broker 地址，默认 redis://localhost:6379/0
    CELERY_RESULT_BACKEND     结果后端，默认同 broker
    CELERY_WORKER_QUEUES      消费队列（逗号分隔），默认 parsing
"""

from __future__ import annotations

import os

try:
    from celery import Celery
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "worker 需要 celery：pip install celery（开发环境见 README 依赖说明）"
    ) from exc

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)
WORKER_QUEUES = [
    name.strip()
    for name in os.getenv("CELERY_WORKER_QUEUES", "parsing").split(",")
    if name.strip()
]

celery_app = Celery("ogas-parsing-worker", broker=BROKER_URL, backend=RESULT_BACKEND)
celery_app.conf.update(
    imports=("worker.services.document_parser.tasks",),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_default_queue="parsing",
)


def main() -> None:
    """以 ``python -m`` 方式启动 worker（Dockerfile 入口）。"""
    celery_app.worker_main(
        ["worker", "-Q", ",".join(WORKER_QUEUES), "--loglevel=info"]
    )


if __name__ == "__main__":
    main()
