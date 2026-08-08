# PDF / Markdown 适配器

## 1. 定位

两个首发适配器。PDF 是真实场景主力（复杂版面、表格、图文混排）；
Markdown 是自举格式（解析器与序列化器互逆，用于测试与文档类输入）。

## 2. PDF 适配器

### 2.1 检测（detect）

- mime：`application/pdf`；扩展名：`.pdf`；魔数：`%PDF-`。
- 输出：`page_count`、`encrypted`、`is_scanned`（按页统计文本量，
  文本稀疏页占比高 → 扫描件）、`needs_ocr`。
- 加密：无密码 → `ENCRYPTED`；有密码尝试解密，失败同上。

### 2.2 提取（extract）

- 引擎：PyMuPDF（fitz）为主，pdfplumber 辅助表格。
- 阅读顺序：按页内 block 坐标（top→bottom, left→right）排序，
  跨页块拆分后拼接；多栏文档用列边界识别。
- 表格：线框/间距规则识别 → 结构化单元格（合并、表头）；
  规则失败时标记，交 LLM 结构阶段兜底。
- 图片：抽取位图 + 位置；题注启发式（相邻"图 N：…"段落）绑定。
- 页眉页脚/水印：按重复模式过滤（保留页码）。
- 边界：超大 PDF 按 `max_pages` 分页批处理；损坏文件返回
  `CORRUPTED`；扫描件 `needs_ocr` 时走 OCR 通道（可插拔，默认关闭）。

### 2.3 结构（流水线统一逻辑，非适配器内）

- 规则优先：字体大小/样式/编号模式（`一、`、`1.1`、`Figure N`）建标题树。
- LLM 兜底：规则置信度低时，把候选段落交 LLM 判定层级，
  输出 schema 校验后并入 IR。
- 失败不影响正文：结构失败仅降级 section_path，不整体失败。

### 2.4 验收标准

- 文本 PDF：正文抽取召回 ≥ 99%，标题层级准确率 ≥ 95%（回归集）。
- 表格：简单表格结构还原 ≥ 95%，合并单元格不丢失。
- 图片：引用位置与题注绑定正确率 ≥ 90%。
- 加密/损坏/扫描件返回正确错误码。

## 3. Markdown 适配器

### 3.1 检测

- mime：`text/markdown`；扩展名：`.md` / `.markdown`；魔数：无。

### 3.2 解析（extract）

- 引擎：markdown-it-py（或自研轻量 parser），产出 IR。
- 覆盖：ATX / setext 标题、嵌套列表、GFM 表格、围栏代码块、
  图片/链接、引用、脚注。
- 无版面信息：`page = null`，`order` 按文档顺序。
- 图片：本地相对路径解析为 asset；远程 URL 记录引用不下载（选项控制）。

### 3.3 与序列化器的互逆性

- `md parse（适配器）↔ md serialize（打包阶段）` 互为逆操作。
- 回归测试：`md → IR → md` 往返一致（规范化后 diff）。
- 该往返测试同时作为 IR 保真度的哨兵。

### 3.4 验收标准

- 标准 Markdown 往返一致率 100%（规范化比较）。
- GFM 表格、围栏代码、嵌套列表无丢失。
- 非法 Markdown 不崩溃，容忍并记录 warning。

## 4. 公共要求（两个适配器都遵守）

- 阶段计时埋点：profile / extract 耗时写入 `job.progress.stages`。
- 资源限制：单文件大小、单块文本长度上限，超限截断 + warning。
- 错误码语义：遵守 02-adapter-interface 第 6 节。
