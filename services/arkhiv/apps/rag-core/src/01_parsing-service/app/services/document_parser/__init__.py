"""文档解析服务核心（MVP 骨架）。

按设计文档 apps/rag-core/docs/01_parsing-service/ 实现：
- IR 模型（01）：ir/ 包，Block 为对外 IR，ParsedRow/DataFrame 为存储视图
- 适配器接口（02）：orchestration/format_adapters.py
- 任务状态机（03）：state_machine/ 包（纯内存实现）
- PDF/Markdown 适配器（04）：formats/ 包
- 产物打包（05）：packaging/ 包

参考实现：Knowhere document_parser。本包为其重构骨架：保留 Protocol 适配器 /
lazy import / Markdown 行扫描状态机 / PDF 分片归 md 的设计，剔除 LLM、MinerU、
DB 与 shared.* 依赖。运行依赖（pandas、pymupdf、Pillow）均为惰性导入。
"""
