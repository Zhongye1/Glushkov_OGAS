# 文档解析服务设计文档

本文档描述 rag-core「文档解析服务」的目标设计。现有代码
`src/01_parsing-service/` 仅作为参考，不构成实现约束；另有一份
可对照的参考实现（Knowhere document_parser），见 `06-reference-implementation.md`。

## 背景

解析服务是 RAG 离线链路的入口：任意格式文档 → 统一中间表示（IR）→
多视图产物包 → 发布给索引与检索。设计遵循 RAG.md 的分层原则：
解析核心只写一遍，REST/MCP 只是薄协议外壳。

解析服务对外提供任务与产物 API（submit / get_result / notify），
接口契约围绕产物包设计；计费、限流、认证是横切层，不与解析核心耦合。

## 文档索引

| 文档                                                       | 内容                                         | 阅读顺序 |
| ---------------------------------------------------------- | -------------------------------------------- | -------- |
| [01-ir-model.md](01-ir-model.md)                           | 统一中间表示（IR）：Block 模型、版本化、校验 | 1        |
| [02-adapter-interface.md](02-adapter-interface.md)         | 格式适配器接口与路由                         | 2        |
| [03-state-machine.md](03-state-machine.md)                 | 解析任务状态机、幂等、重试                   | 3        |
| [04-adapters-pdf-markdown.md](04-adapters-pdf-markdown.md) | PDF / Markdown 两个首发适配器                | 4        |
| [05-artifact-packaging.md](05-artifact-packaging.md)       | 产物打包、存储布局、发布                     | 5        |
| [06-reference-implementation.md](06-reference-implementation.md) | 参考实现对照（Knowhere document_parser）     | 6        |

## 架构关系

```text
submit (REST) → 状态机(job) → 适配器(detect/extract) → IR
    → structure/serialize/chunk（统一流水线）→ 产物包 → 发布(索引/回调)
```

- IR 是服务内部的产品定义，所有下游只消费 IR。
- 适配器负责「源格式 → IR」，新格式 = 新适配器，不动流水线。
- 状态机负责可靠性：幂等、重试、崩溃恢复、通知。
- 产物包是服务的交付物，也是计费与评测的数据来源。

