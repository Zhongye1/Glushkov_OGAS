# 参考实现对照（Knowhere document_parser）

## 1. 背景与定位

本仓库的目标设计（01–05）在落地前，有一份可对照的参考实现：

- 位置：`/home/franka/WorkSpace01/knowhere/apps/worker/app/services/document_parser/`
- 与 arkhiv 的关系：它是**独立的解析内核**（无 API），而本仓库
  `src/01_parsing-service/` 是 **API/编排壳**（jobs/billing/rate_limit/
  retrieval，且引用的 `app.core.tasks.document_ingestion_tasks.parse_task`
  尚未实现）。两者是互补关系，不是同一份代码。
- 本文档记录对参考实现逐点核实后的结论，作为「哪些可直接抄、哪些要替换」
  的依据。下面所有文件路径均相对参考实现根目录。

## 2. IR：扁平 DataFrame + ParsedRow

参考实现没有 Block 树，对外 IR 就是一张 `pandas.DataFrame`，每行一个
`ParsedRow`（`support/parser_rows.py:54`）。

| 字段 | 说明 |
| --- | --- |
| `content` / `path` / `type` / `know_id` / `addtime` | 必需五字段 |
| `keywords` / `summary` / `tokens` / `connectto` / `page_nums` / `length` / `entities` / `asset_title` | 可选字段 |

关键设计细节：

- **列定义 env 驱动**：`PARSER_ROW_COLUMNS` 由 `settings.ALL_DF_COLS` 切出，
  再强制补尾部 `entities`、`asset_title`（`support/parser_rows.py:16`）。
  注释明确说明：兼容只声明 legacy 11 列的老环境变量，否则按列名写入会在
  导入期 `ValueError`。代价是列顺序被 env 绑定。
- **层级编码进 path**：章节关系用 `split_char` 拼成
  `relative_root/一级标题/二级标题` 字符串，不用父子指针；树结构由
  `page_memory` 层重建。
- **位置顺序手工对齐**：`to_list()`（`:69`）的顺序**不等于** dataclass 字段
  声明顺序（`length` 被插到第 3 位）；`to_dict()` 用
  `zip(PARSER_ROW_COLUMNS, to_list())`（`:87`）组回。两套顺序分离，正是
  `COL_KEYWORDS / COL_SUMMARY / COL_ENTITIES / COL_ASSET_TITLE` 索引常量
  （`:111-114`）存在的原因，LLM 摘要回写走
  `apply_body_summary / apply_asset_summary`（`:117/:129`），
  `_ensure_row_width` 负责把 legacy 11 列的行补齐到当前宽度。

与目标设计（01-ir-model）的差异：参考实现是「一行一语义、直接可入库」，
代价是失去树结构与版面追溯；目标设计用 Block 树 + `section_path`，保留
可追溯性，代价是模型更重。落地时建议以目标设计为主，参考实现的
「列契约 + 索引常量」模式可直接吸收进 IR 序列化层。

## 3. 适配器：Protocol + frozen dataclass + lazy import

接口形状（`orchestration/format_adapters.py:10`）：

```python
class DocumentParseAdapter(Protocol):
    @property
    def document_format(self) -> object: ...

    def parse(self, session: ParseSession) -> ParseOutput: ...
```

- 全部适配器是 `@dataclass(frozen=True)`，解析逻辑在 `parse()` 方法体内
  懒加载，加载路由表时不拉入 pymupdf/python-docx 等重依赖。
- 适配器清单：

| 适配器 | 行为 | 备注 |
| --- | --- | --- |
| `FragmentParseAdapter` | 片段直接入 df | |
| `TextParseAdapter` | `parse_texts` → `parse_md` | 收敛到 md 轨 |
| `ImageParseAdapter` | 单图解析 | |
| `PdfParseAdapter` | `parse_pdfs` | Deprecated → page_memory |
| `DocParseAdapter` | `doc_to_docx` 后复用 docx 解析 | 老格式归一 |
| `DocxParseAdapter` | docx 解析 | |
| `XlsParseAdapter` | `xls_to_xlsx` 后复用 xlsx 解析 | 老格式归一 |
| `XlsxParseAdapter` | xlsx 解析 | |
| `PptxParseAdapter` | `parse_pptx` | Deprecated → page_memory |
| `MarkdownParseAdapter` | `parse_md` | |
| `HtmlParseAdapter` | HTML → md 管线 | 收敛到 md 轨 |
| `JsonParseAdapter` | 返回 `parsed_df=None` | 占位 |

- 路由：`resolve_document_format` 按扩展名判出 `DocumentFormat` 枚举
  （`orchestration/format_router.py:47`），`validate_office_container` 校验
  office 容器，`get_document_parse_adapter` 从 dict 字面量取适配器实例
  （`:85`）。加格式只动枚举 + 路由表 + 一个适配器。
- 该 Protocol + frozen dataclass + lazy import 骨架可直接照搬，替换内部
  解析实现即可。

## 4. 两层「状态机」：管线层与行扫描层

参考实现里没有显式 FSM 引擎，所谓状态机分两处：

1. **管线级线性流转**（`orchestration/parse_pipeline.py:13`）：
   `build_parse_session → route_document_parse → apply_parse_postprocess`，
   最后 `with_dataframe` 返回新对象（`ParseOutput` 是 frozen dataclass）。
   注意 `build_parse_session`（`orchestration/parse_session.py:59`）内部还
   执行了 `profile_document`（`stage_timer("document.profile")`，`:86`），
   所以严格是 profile + 建会话 → 路由 → 后处理三段。
2. **Markdown 行扫描状态机**（`formats/markdown/parse_state.py:27`）：
   `MarkdownParseState` 维护 `path_stack`（标题层级栈）、`base_level`（扫描
   中遇到的最小级别，用于 H2 起步文档归一）、`path_counter`（同名路径
   `_2/_3` 去重）、`content_items`（当前块累积正文）、`table_lines`、
   `seen_images`、`image_count/table_count`、`deferred_llm_tasks`（延迟到
   最后批量跑的 LLM 摘要任务）。
   - `enter_heading`（`:89`）：弹掉栈中 `level >= adjusted` 的项 → 算
     `adjusted_level` → 拼 path → 处理同名 → 压栈。
   - `record_page_marker`（`:52`）：跳过 `<!--page-->` 类 HTML 注释，注释
     说明页码追踪已移除，未来交给 PAGE MEMORY。
   - `to_dataframe`（`:151`）：positional rows 组装 `ParsedRow` 后
     `process_dup_paths_df` 处理重复 path。
   - 该引擎被 Markdown/PDF/Text/Html 多个适配器共用。

与目标设计（03-state-machine）的关系：参考实现的「管线层」对应目标设计的
流水线编排，但**任务级状态机（pending → waiting-file → running → done/
failed）、幂等、重试、崩溃恢复在参考实现里没有**，这些是目标设计需要补齐
的部分。

## 5. PDF 归约到 Markdown

`parse_pdfs`（`formats/pdf/parser.py:19`）三分支：

1. Atlas 图册类：`profile.routing_category is PdfRoutingCategory.ATLAS` 时
   直接 `parse_atlas`，绕过 MinerU（`:33`）。
2. `profile.anatomy` 存在：进分片管线 `_parse_pdf_via_shards`（`:90`）。
3. 否则标准单趟：MinerU 抽 `full.md` → `parse_md(skip_toc_detection=True)`
   （`:86`）。

分片管线 docstring 共 **7 步**（不是 8 步）：

```text
1. DOC_AGENT → shard plan + TOC
2. bin_pack → merged shards
3. split_pdf（exclude TOC pages）
4. MinerU per shard（并行）
5. 逐片标题预测（并行，非首片用 split_toc_for_shard 切 TOC 区间）
6. merge_shard_lines + merge_images
7. parse_md Phase B（跳过 TOC 检测与标题预测）
```

- `bin_pack_shards` 是 1:1 映射（`formats/pdf/shard_splitter.py:34`），注释
  说明 agent 已在 H1/H2 语义边界切好，合并会跨边界降低标题预测质量。
- `split_pdf` 用 PyMuPDF 逐页切分，`exclude_pages` 剔目录页，并维护
  `page_remap`（shard 本地 0-based → 原始 1-based 页号）（`:50`）。
- 单片且无 TOC 页走 `fast_path_original_pdf`，直接复用原 PDF/S3 对象
  （`parser.py:165`）。
- `finally` 里 `_cleanup_temp_shard_s3_assets` + `_cleanup_local_shard_workspace`
  兜底清理（`:356-357`）。
- `parse_md` 分 Phase A（TOC 检测 + 标题预测）/ Phase B（`MarkdownParseState`
  遍历），分片管线只跑 Phase B。

设计要点：PDF 不造独立逻辑，而是**把任意 PDF 归约成一批带标题的 md 行，
再灌进同一台行扫描状态机**——这是「一套 IR 覆盖多格式」的根本原因。

## 6. 产物打包与稳定接缝

- 双产物：磁盘目录 + `ParseOutput(output_dir, parsed_df)`。
- `_resolve_output_paths`（`orchestration/parse_session.py:105`）建
  `full_output_dir`，用 `os.path.commonpath` 校验防止路径逃逸出 workspace。
- 后处理 `apply_parse_postprocess`（`orchestration/postprocess.py:24`）：
  1. `cleanup_unreferenced_images`（`:50`）：删未被 `tables/*.html` 引用的
     hash 命名孤儿图；`image-N-*` 与表格 HTML 引用的 hash 图保留。
  2. `compress_output_images`：PNG→JPG、resize，产生 `rename_map`。
  3. `apply_rename_map_to_dataframe`：把 df 里引用的图片路径同步改名，
     保证磁盘文件名与 DataFrame 内容一致。
- 阶段名 `document.cleanup_unreferenced_images` / `document.compress_images`
  与参考产物 `manifest.json` 的 `stages.timing_ms` 对应。
- 对外稳定入口 `checkerboard_parse_output`（`parse_service.py:10`），docstring
  即 "Stable parser seam backed by dedicated orchestration modules"，内部
  编排怎么改都不影响调用方。

## 7. 与目标设计的差距与内化清单

| 维度 | 参考实现 | 目标设计 | 动作 |
| --- | --- | --- | --- |
| IR | 扁平 DataFrame + path 字符串 | Block 树 + section_path | 以目标设计为主，吸收列契约/索引常量模式 |
| 适配器 | Protocol + frozen + lazy import | 同左 + detect() 能力声明 | 直接照搬骨架 |
| 任务状态机 | 无（只有管线线性流） | pending→…→done/failed + 幂等/重试 | 需补齐 |
| PDF | MinerU + 分片归 md | 同思路，解析引擎可插拔 | 保留分片管线，替换 MinerU provider |
| 打包 | 目录 + df，后处理图文一致 | 产物包 + manifest + 发布 | 合并：manifest 已有，补发布钩子 |
| 配置 | `shared.core.config` env 驱动列 | 明确的 schema 版本化 | 需替换/收敛 |

内化动作建议：

1. 把 knowhere `document_parser` 包搬入 `01_parsing-service`（`support/`、
   `orchestration/`、`formats/`、`conversion/`、`assets/`、`profiling/`）。
2. 落地任务状态机（03-state-machine）并接到 `worker_dispatcher.py` 的
   `parse_task`。
3. 以目标 IR（01）为准做一层序列化适配，兼容现有 `ParsedRow` 列契约。
4. 将 MinerU provider、`shared.core.config` 收敛为可插拔配置，不再被
   env 绑定列顺序。
