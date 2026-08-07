"""MCP 协议外壳：把内核 retrieve() 暴露为工具，供 Cursor / Claude Code 等调用。"""

from typing import Any

from mcp.server.mcpserver import MCPServer

from src.kernel import get_kernel

mcp = MCPServer(name="ogas-rag", version="0.1.0")


@mcp.tool(description="从业务知识库检索与 query 相关的片段（含来源路径与行号）")
async def retrieve(query: str, top_k: int = 10) -> list[dict[str, Any]]:
    """从业务知识库检索与 query 相关的片段（含来源路径与行号）。"""
    chunks = await get_kernel().retrieve(query, top_k=top_k)
    return [chunk.model_dump() for chunk in chunks]


def main() -> None:
    mcp.run()  # 默认 stdio 传输


if __name__ == "__main__":
    main()
