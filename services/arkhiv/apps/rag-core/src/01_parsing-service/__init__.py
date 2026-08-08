"""文档解析 worker：队列消费者，无 HTTP 接口、无用户鉴权。

鉴权、建 job、查进度/结果等入口职责在 API 层；本包只包含解析内核
（app/services/document_parser/）与 worker 入口（worker_app.py）。
"""
