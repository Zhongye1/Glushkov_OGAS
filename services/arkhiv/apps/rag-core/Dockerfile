# API 镜像：FastAPI 编排（REST / MCP）。解析 worker 见 Dockerfile.worker。
# 构建（build context = services/arkhiv 仓库根）：
#   docker build -f apps/rag-core/Dockerfile -t ogas-rag-core .
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装共享契约层（ogas-rag-core 的依赖），再装应用
COPY packages/shared-python ./packages/shared-python
COPY apps/rag-core/pyproject.toml ./apps/rag-core/pyproject.toml
COPY apps/rag-core/src ./apps/rag-core/src

RUN pip install --no-cache-dir ./packages/shared-python && \
    pip install --no-cache-dir ./apps/rag-core && \
    pip install --no-cache-dir uvicorn

EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
