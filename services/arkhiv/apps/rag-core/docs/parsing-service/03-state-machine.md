# 解析任务状态机

## 1. 定位

状态机负责解析任务的可靠性：幂等、状态流转、重试、崩溃恢复与通知。
所有状态迁移落库、可查询、可审计。

## 2. 状态定义

| 状态           | 含义                                  |
| -------------- | ------------------------------------- |
| `pending`      | 已创建，等待文件/URL 到位             |
| `waiting-file` | 已确认上传，等待文件落库              |
| `running`      | 解析流水线执行中                      |
| `converting`   | 结构增强/LLM 阶段（running 的子状态） |
| `done`         | 解析成功，产物已打包                  |
| `failed`       | 解析失败（含错误码）                  |
| `cancelled`    | 用户/系统取消                         |

## 3. 迁移表

| from                             | to           | 触发                    | 守卫         |
| -------------------------------- | ------------ | ----------------------- | ------------ |
| pending                          | waiting-file | 确认上传                | 文件存在     |
| pending                          | running      | URL 直达                | 无需文件     |
| waiting-file                     | running      | 文件落库完成            | 文件存在     |
| running                          | converting   | 进入 LLM 结构阶段       | —            |
| converting                       | running      | 结构阶段完成            | —            |
| running / converting             | done         | 产物打包完成            | 产物校验通过 |
| running / converting             | failed       | 不可重试错误 / 重试耗尽 | 错误码       |
| running / converting             | running      | 阶段重试                | 可重试错误码 |
| pending / waiting-file / running | cancelled    | 取消请求                | 未进入 done  |

约束：`done / failed / cancelled` 为终态，不可再迁移。

## 4. 阶段级子状态

任务内部分为 profile → extract → structure → serialize → chunk → package。
子状态存于 `job.progress`（JSON），用于观测与断点续跑：

```json
{
    "stage": "structure",
    "stage_started_at": "...",
    "attempt": 2,
    "stages": {
        "profile": { "status": "done", "duration_ms": 120 },
        "extract": { "status": "done", "duration_ms": 8450 }
    }
}
```

## 5. 幂等与去重

- `job_id` 幂等：同一 job 的 create/confirm 重复请求返回已有状态。
- 内容去重：`source_hash` 相同且文档未变更时，直接复用已有
  `document_id` 与产物，不重复解析、不重复计费。
- 发布幂等：产物与通知按 `document_id` + `ir_version` 幂等，可重发。

## 6. 重试与退避

| 维度     | 规则                                      |
| -------- | ----------------------------------------- |
| 触发条件 | 可重试错误码（如 `EXTRACTION_FAILED`）    |
| 次数上限 | 阶段 3 次，任务整体 5 次                  |
| 退避     | 指数退避 + 抖动：1s / 5s / 30s / 2m / 10m |
| 耗尽     | 任务置 `failed`，带最终错误码与错误详情   |
| 死信     | 可选：进入死信队列供人工重放              |

## 7. 崩溃恢复

- worker 领取任务时写入 `lease: {worker_id, expires_at}`。
- 心跳续租；`running` 超过租期未续 → 判定 stale → 重投队列（attempt+1）。
- 重投后从 `job.progress.stage` 断点继续，而非整任务重跑。

## 8. 数据模型（job 表）

| 字段                                         | 说明       |
| -------------------------------------------- | ---------- |
| `job_id`                                     | 主键       |
| `status`                                     | 状态枚举   |
| `stage`                                      | 当前阶段   |
| `attempt`                                    | 已尝试次数 |
| `error_code` / `error_message`               | 失败归因   |
| `lease_worker` / `lease_expires_at`          | 租约       |
| `source_hash` / `document_id`                | 幂等键     |
| `created_at` / `started_at` / `completed_at` | 时间线     |

## 9. 事件通知

- 迁移到 `done` / `failed` 时发送 webhook 通知（QStash），载荷含
  `job_id`、`status`、`document_id`、`error`。
- 通知幂等：以 `job_id + status` 去重，支持重发。
- 通知失败不影响任务终态，由独立重发任务补偿。

## 10. 并发控制

- 单 job 单 worker：租约互斥。
- 每用户并发上限 + 全局并发上限（承接现有限流/计费准入思路）。
- 队列按优先级/来源分流：demo、用户上传、批量迁移分队列。
