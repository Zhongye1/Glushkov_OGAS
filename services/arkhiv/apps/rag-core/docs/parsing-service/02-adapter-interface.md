# 适配器接口

## 1. 定位

适配器负责「源格式 → IR」。解析流水线的 profile / normalize / extract 属于
适配器职责；structure（标题层级）、serialize、chunk 是**所有格式共用**的
流水线逻辑，不进适配器。

新增格式 = 新增一个适配器，不改流水线。

## 2. 适配器生命周期

```text
ParsingInput
  → detect()        探测格式、加密、扫描件（适配器内）
  → normalize()     转中间态（可选，适配器内）
  → extract()       产出 blocks + assets（适配器内）
  → [流水线] structure / serialize / chunk / package
```

## 3. 接口定义（Python Protocol）

```python
class DocumentAdapter(Protocol):
    """任意格式 → IR blocks + assets。"""

    # 路由元数据
    format_name: str
    extensions: frozenset[str]
    mimes: frozenset[str]
    priority: int = 0          # 越大越优先；同格式多适配器时用

    def supports(self, *, extension: str, mime: str) -> bool: ...

    async def detect(self, input: ParsingInput) -> DetectionResult: ...

    async def extract(
        self,
        input: ParsingInput,
        options: ParseOptions,
    ) -> ExtractionResult: ...
```

### 3.1 输入

```python
@dataclass(frozen=True)
class ParsingInput:
    source: bytes | str        # 文件字节 或 URL
    source_name: str
    mime: str | None
    extension: str | None
```

### 3.2 检测结果

```python
@dataclass(frozen=True)
class DetectionResult:
    format_name: str
    confidence: float          # 0~1
    is_scanned: bool           # PDF：是否扫描件
    needs_ocr: bool
    encrypted: bool
    page_count: int | None
    warnings: tuple[str, ...] = ()
```

`detect` 决定路由与能力声明：文本 PDF 直接走文本提取；扫描件标记
`needs_ocr`，由流水线决定是否启用 OCR 或返回 `SCANNED_NO_OCR` 错误。

### 3.3 提取结果

```python
@dataclass(frozen=True)
class ExtractionResult:
    blocks: list[Block]        # 按阅读顺序
    assets: list[Asset]        # 图片/表格文件本体或引用
    warnings: tuple[str, ...] = ()
```

### 3.4 解析选项

```python
@dataclass(frozen=True)
class ParseOptions:
    lang: str | None = None
    parse_track: str = "chunk"       # chunk | page_memory
    ocr_fallback: bool = True
    extract_images: bool = True
    extract_tables: bool = True
    max_pages: int | None = None
```

## 4. 路由与注册

- 注册表：`extension / mime → adapter 列表`，按 `priority` 排序。
- 路由顺序：显式 mime 匹配 → 扩展名匹配 → `detect()` 探测降级。
- 降级示例：`application/octet-stream` 按扩展名走，扩展名也无 →
  按魔数探测；PDF 文本层失败可降级 OCR。
- 探测失败：返回 `UNSUPPORTED_FORMAT` 错误码，不静默解析。

## 5. 输出约束（流水线强制校验）

| 约束     | 说明                                                      |
| -------- | --------------------------------------------------------- |
| IR 合法  | 提取结果必须通过 IR schema 校验（见 01-ir-model 第 7 节） |
| 顺序完整 | `order` 连续，正文不丢失阅读顺序                          |
| 引用闭合 | image/table 的 asset 引用必须能在 `assets` 中解析         |
| 体积上限 | 单块文本、单图体积超限时截断并记 warning                  |

## 6. 错误分类（适配器层错误码）

| 错误码               | 含义                | 可重试       |
| -------------------- | ------------------- | ------------ |
| `ENCRYPTED`          | 文件加密/需要密码   | 否           |
| `CORRUPTED`          | 文件损坏            | 否           |
| `SCANNED_NO_OCR`     | 扫描件但 OCR 不可用 | 是（配置后） |
| `UNSUPPORTED_FORMAT` | 无适配器            | 否           |
| `EXTRACTION_FAILED`  | 提取过程异常        | 是           |
| `RESOURCE_LIMIT`     | 超页数/超大小       | 否           |

错误码由状态机消费：可重试的进重试队列，不可重试的直接 failed
（见 03-state-machine）。

## 7. 新增格式清单

1. 实现 `DocumentAdapter`（detect + extract）。
2. 注册 extensions/mimes 与优先级。
3. 用 IR 校验器跑通合法产物。
4. 补充回归样例（至少一份正常文档 + 一份边界文档）。
5. 在适配器评估表中登记：格式、覆盖能力、已知限制。
