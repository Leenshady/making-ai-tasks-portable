---
name: task-portability
description: "Decouple AI tasks from any specific workbench, model, or platform by snapshotting a task's full state into a portable, self-contained bundle (Markdown + JSON). Lets any AI or human resume the task in any environment with minimal migration cost. Use when the user wants to make an AI task portable, migrate a task between environments, hand off a task to another model/tool, checkpoint a task before switching context, or freeze task state (goal, progress, decisions, TODOs, files, dependencies). Works both before a task starts (initialization) and during a task (incremental checkpoint)."
description_zh: "将 AI 任务从具体工作台/模型/平台中解耦，把任务完整状态固化成可移植的自包含快照（Markdown + JSON），让任意 AI 或人可在任意环境以最小迁移成本接续任务。"
description_en: "Decouple AI tasks from workbench/model/platform by snapshotting task state into portable bundles."
version: 1.0.0
author: "Leenshady"
display_name: "让 AI 任务可迁移"
display_name_en: "Make AI Tasks Portable"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - AskUserQuestion
examples_zh:
  - "把这个任务快照一下"
  - "开始一个可迁移的任务"
  - "我要换个环境继续做这个任务，帮我打包迁移"
  - "把这个任务交接给别人"
examples_en:
  - "Snapshot this task's current state"
  - "Start a portable task"
  - "Package this task for migration to another environment"
  - "Hand off this task to someone else"
---

# 让 AI 任务可迁移（Task Portability）

你的职责是**把一个 AI 任务的"状态"从执行环境里剥离出来**，固化成**模型无关、平台无关、自包含**的数据，让任意 AI 或人读取一份快照即可无缝接手，从而解除对具体工作台与模型的依赖，把迁移成本降到最低。

## 核心思想

一个 AI 任务的真正资产不是"它跑在哪个工具上"，而是三样东西：

1. **上下文**（Context）—— 目标、约束、背景、关键决策
2. **进度**（Progress）—— 做完了什么、做到哪一步、下一步是什么
3. **工件**（Artifacts）—— 产出了哪些文件、依赖哪些资源、环境要求是什么

只要这三样被**冻结成自包含的数据**，任务就不再被任何单一环境绑架。快照本身就是"可迁移的任务"。

## 产出物：任务快照包（Task Bundle）

> 生成快照前，先参考 `@references/example-snapshot.md` 中一份合格快照的完整示例，确保字段齐全、语气一致。

每次快照都在一个目录下产出两个互补文件：

每次快照都在一个目录下产出两个互补文件：

```
<task-slug>/
├── task-snapshot.md    # 人类可读：任意 AI 或人读这一份即可接手
├── task-snapshot.json  # 可编程：可校验、可转换、可被工具消费
└── artifacts/          # 可选：任务相关的关键工件清单（不复制文件，只记录路径）
```

### 为什么是双格式

- **Markdown**：零门槛。任何模型、任何编辑器、甚至人，读一遍就能理解任务全貌并继续做。这是"模型无关"的根基。
- **JSON**：结构化。可被脚本校验、转换（如转成 A2A 任务卡、转成其他框架格式）、或做 diff 追踪增量。这是"平台无关 + 可迁移"的根基。

两者描述**同一份状态**，Markdown 是 JSON 的呈现层，JSON 是 Markdown 的结构层。改一处必须同步另一处。

## 快照内容规范（必须完整覆盖）

一份合格快照必须包含以下字段，**缺一不可**：

### 1. 身份与元信息（identity & meta）
- `task_id`：任务唯一标识（如 `task-20261102-1530`，用日期+时间生成，避免冲突）
- `title`：一句话任务标题
- `slug`：文件安全的任务短名（小写、连字符）
- `created_at` / `updated_at`：ISO 8601 时间戳（**必须用 `date` 命令获取，禁止手算**）
- `status`：`initialized` | `in-progress` | `checkpointed` | `completed` | `abandoned`
- `version`：快照格式版本

### 2. 目标与约束（goal & constraints）
- `goal`：任务最终要达成的结果，用可验证的语句描述
- `success_criteria`：如何判定"做完了"（可观测、可检验）
- `constraints`：硬性限制（技术栈、禁止事项、合规要求、范围边界）
- `non_goals`：明确**不做**什么，防止接手者跑偏

### 3. 上下文与背景（context）
- `background`：为什么做这个任务、前置背景
- `key_decisions`：已做过的关键决策 + 决策理由（这是最容易被丢失、最有价值的资产）
- `assumptions`：当前基于哪些假设，哪些尚未验证
- `terminology`：任务中的专有名词/约定，避免接手者理解偏差

### 4. 进度与计划（progress & plan）
- `completed`：已完成事项清单（具体、可核对）
- `in_progress`：正在做的事，以及做到哪一步（越细越好）
- `next_steps`：明确的下一步行动，按优先级排序
- `blockers`：卡点、未解问题、需要的输入
- `risks`：潜在风险与规避建议

### 5. 工件与依赖（artifacts & dependencies）
- `files`：任务涉及/产出的关键文件清单（**绝对路径 + 作用说明**，不复制文件本体）
- `dependencies`：外部依赖（SDK、API key、数据源、权限），以及**获取方式**
- `environment`：运行环境要求（OS、运行时、版本）
- `commands`：关键命令/操作记录（可复现）

### 6. 恢复指引（resume guide）
- `how_to_resume`：接手者第一件事该做什么、从哪个文件/步骤接着做
- `contact`：遇到歧义时如何联系任务发起者（可选）
- `handoff_notes`：任何"口口相传才会知道"的隐性知识，**必须写下来**

## 两个接入时机（都要支持）

### 时机 A：任务开启前（初始化快照）
用户说"开始一个可移植的任务"或"把这个任务做成可迁移的"。此时只有目标、约束、背景，没有进度。产出**初始快照**，`status = initialized`，把目标/约束/背景填满，进度区留空但结构完整。

### 时机 B：任务过程中（增量/断点快照）
用户说"快照一下当前进度""把这个任务打包迁移""我要换个环境继续做"。此时任务已有大量状态。产出**增量快照**，重点抓取：
- 已完成事项与关键决策（最易丢失）
- 未完成项与下一步
- 文件清单与依赖
- 用 `updated_at` 标记时间，用版本号或序号标记增量

**关键原则：快照是"冻结点"，不是"日志"。** 每次快照都应是**自包含的完整状态**，接手者只读最新一份即可，不需要回看历史。

## 工作流（执行步骤）

### 步骤 1：确认任务与范围
- 用 AskUserQuestion 或直接询问，确认：任务目标、当前阶段（未开始/进行中）、是否已有可迁移的内容
- 若信息不足，宁可先问清楚，不要臆测填充

### 步骤 2：收集状态
- 从当前对话、工作目录、已有文件里提取：目标、约束、决策、进度、文件、依赖
- 读关键文件以核实状态（不要凭印象写）
- 用 `date` 命令获取准确时间戳

### 步骤 3：生成快照包
- 确定 `slug` 与快照目录位置（默认放在任务工作目录下，如 `<cwd>/.task-portability/<slug>/`；用户指定则用指定位置）
- 先写 JSON（结构完整、字段齐全），再据 JSON 生成 Markdown（两者一致）
- 确保自包含：读这一份 Markdown 即可完全接手

### 步骤 4：自检
逐项核对以下问题：
- [ ] 目标是否可验证？成功标准是否可观测？
- [ ] 关键决策是否都记录了理由？
- [ ] 进度是否具体到"接手者能接着做"的程度？
- [ ] 文件清单是否绝对路径 + 作用说明？
- [ ] 依赖是否有获取方式？
- [ ] 隐性知识是否写进了 `handoff_notes`？
- [ ] Markdown 与 JSON 内容是否一致？

### 步骤 5：交付与说明
- 报告快照包位置、两个文件的作用
- 说明接手者只需读 `task-snapshot.md` 即可接手；需要程序化处理时用 JSON
- 提示：任务未完成时，建议在关键节点重复快照，保持快照"最新即完整"

## 迁移与恢复（接手者视角）

当用户是"接手方"，拿到一个快照包时：
1. **先读 `task-snapshot.md` 的 `how_to_resume`**，按指引从正确位置接手
2. 对照 `completed` / `in_progress` / `next_steps` 明确自己在哪一步
3. 检查 `dependencies` 与 `environment` 是否满足，缺什么先补齐
4. 有歧义先看 `handoff_notes` 和 `key_decisions`，仍不确定则找 `contact`
5. 从 `next_steps` 的第一项开始继续

## 硬性规则

1. **禁止手算时间戳**——一律用 `date` 命令获取当前时间。
2. **禁止凭印象写状态**——文件、进度、决策必须核实后写。
3. **禁止只写 Markdown 或只写 JSON**——必须双格式同步产出。
4. **禁止只写"快照"不写"恢复"**——没有 `how_to_resume` 的快照是废的。
5. **快照自包含**——接手者只读最新一份快照 + 快照里指向的文件即可接手，不能要求"回看历史对话"。
6. **路径用绝对路径**——相对路径在不同环境下会失效，违背可移植目标。
7. **不复制大文件**——`files` 只记录路径与作用，不把文件本体塞进快照（除非用户明确要求打包）。

## 常见场景速查

| 用户意图 | 你的动作 |
|---|---|
| "把这个任务做成可迁移的" / "开始一个可移植任务" | 初始化快照（时机 A） |
| "快照一下当前进度" / "打个断点" | 增量快照（时机 B） |
| "我要换个环境/换模型继续做" | 增量快照 + 重点写恢复指引 |
| "把这任务交接给 X" | 增量快照 + 重点写 handoff_notes 和 key_decisions |
| "把任务打包带走" | 增量快照，若用户要，用 zip/tar 打包快照目录 |
| 拿到一个快照包要接手 | 走"迁移与恢复"流程 |
