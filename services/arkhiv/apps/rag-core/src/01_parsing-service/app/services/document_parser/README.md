# document_parser：文档解析服务核心（MVP 骨架）

对应设计文档：`apps/rag-core/docs/parsing-service/`（01 IR / 02 适配器 /
03 状态机 / 04 PDF+Markdown / 05 打包 / 06 参考实现对照）。

## 结构

```text
document_parser/
├── ir/            # Block（对外 IR）+ ParsedRow/DataFrame（存储视图）
├── state_machine/ # 任务级状态机（pending→…→done/failed，纯内存）
├── support/       # 阶段计时、标识符工具
├── orchestration/ # ParseInput/Session/Output、适配器、路由、流水线、后处理
├── profiling/     # 文档画像（页数/加密探测）
├── formats/
│   ├── markdown/  # 行扫描状态机（Markdown/PDF 共用引擎）
│   └── pdf/       # 文本提供器 + 分片归 md
├── packaging/     # manifest / chunks / 各视图写入（原子提交：manifest 最后写）
└── parse_service.py  # checkerboard_parse_output（stable seam）+ parse_job（FSM 接线）
```

## 依赖

核心逻辑零硬依赖；可选能力惰性导入：

- `pandas`：ParsedRow/DataFrame 视图（`ir/parsed_row.py`、`parse_state.to_dataframe`）
- `pymupdf`：PDF 文本层抽取与分片（`formats/pdf/`）
- `Pillow`：产物图片压缩（`orchestration/postprocess.py`，当前为 no-op 占位）

## 用法

```python
from app.services.document_parser.parse_service import parse_job

result, state = parse_job("/tmp/sample.md", "sample.md", "/tmp/out")
print(state.status)              # JobStatus.DONE
print(result.blocks)             # IR Block 列表
# 产物目录：full.md / chunks.json / doc_nav.json / toc_hierarchies.json / manifest.json
```

## 与参考实现的差异（重构点）

- 去掉 `shared.*`、loguru、LLM、MinerU、DB 依赖；错误码、列契约、状态机保留。
- IR 以 Block 为主，`to_blocks()` 由 MarkdownParseState 的 positional rows 派生。
- PDF 标准轨用 PyMuPDF 文本层（`PdfTextProvider` 可插拔，MinerU 按同一 Protocol 接入）。
- 分片管线保留 7 步结构；逐片标题预测、TOC 排除、并行化为 TODO。
