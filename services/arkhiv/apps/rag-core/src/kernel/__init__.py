"""协议无关的 RAG 内核。

只暴露 retrieve() / answer() 两个语义化入口，任何协议外壳都不得绕过内核。
"""

from src.api.schemas import Answer, Chunk
from src.kernel.base import InMemoryKernel, RAGKernel

__all__ = ["Answer", "Chunk", "InMemoryKernel", "RAGKernel"]


def get_kernel() -> RAGKernel:
    """返回当前内核实现（TODO: 按配置切换到生产实现）。"""
    return InMemoryKernel()
