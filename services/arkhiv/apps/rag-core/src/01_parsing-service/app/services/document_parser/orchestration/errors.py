"""解析层异常与错误码（设计文档 02 §6）。"""

from __future__ import annotations


class ParserError(Exception):
    """解析层基类异常。"""

    error_code: str = "PARSE_FAILED"


class UnsupportedFormatError(ParserError):
    """无适配器 / 未注册格式。"""

    error_code = "UNSUPPORTED_FORMAT"


class EncryptedDocumentError(ParserError):
    """文件加密/需要密码。"""

    error_code = "ENCRYPTED"


class CorruptedDocumentError(ParserError):
    """文件损坏。"""

    error_code = "CORRUPTED"


class ResourceLimitError(ParserError):
    """超页数 / 超大小。"""

    error_code = "RESOURCE_LIMIT"


class ExtractionFailedError(ParserError):
    """提取过程异常（可重试）。"""

    error_code = "EXTRACTION_FAILED"
