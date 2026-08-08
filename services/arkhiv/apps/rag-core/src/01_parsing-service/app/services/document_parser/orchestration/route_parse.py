"""路由：扩展名 → 枚举 → 适配器（参考实现移植）。

参考实现的 validate_office_container 服务于 office 老格式转换，MVP 无
office 适配器，故省略；恢复时在 route_document_parse 中插回即可。
"""

from __future__ import annotations

from app.services.document_parser.orchestration.format_router import (
    get_document_parse_adapter,
    resolve_document_format,
)
from app.services.document_parser.orchestration.parse_output import ParseOutput
from app.services.document_parser.orchestration.parse_session import ParseSession


def route_document_parse(session: ParseSession) -> ParseOutput:
    """把解析会话路由到对应适配器并返回统一输出。"""
    document_format = resolve_document_format(session.file_full_path)
    adapter = get_document_parse_adapter(document_format)
    return adapter.parse(session)
