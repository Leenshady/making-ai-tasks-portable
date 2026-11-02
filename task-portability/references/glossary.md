# 术语对照（Glossary）

本文件提供 skill 中关键术语的中英对照，供跨语言模型接手时参考，确保语义不偏差。

| 中文术语 | English Term | 说明 |
|---|---|---|
| 任务快照 | Task Snapshot | 冻结任务状态的自包含数据（Markdown + JSON） |
| 快照包 | Snapshot Bundle | 一次快照产出的完整目录（含 md + json + artifacts） |
| 自包含 | Self-contained | 只读最新一份快照即可接手，无需回看历史 |
| 上下文 | Context | 目标、约束、背景、关键决策 |
| 进度 | Progress | 已完成、进行中、下一步、阻塞项、风险 |
| 工件 | Artifacts | 任务涉及/产出的文件、依赖、环境 |
| 关键决策 | Key Decisions | 已做的决策及理由（最易丢失的资产） |
| 隐性知识 | Tacit Knowledge | "口口相传才会知道"、需写进交接备注的内容 |
| 交接备注 | Handoff Notes | 记录隐性知识、便于接手者理解的说明 |
| 恢复指引 | Resume Guide | 告诉接手者如何接着做的说明（how_to_resume） |
| 成功标准 | Success Criteria | 可观测、可检验的"做完了"判定 |
| 约束 | Constraints | 硬性限制（技术栈、禁止事项、合规、范围） |
| 不做的事 | Non-goals | 明确不做的内容，防止接手者跑偏 |
| 冻结 | Freeze | 把运行时状态固化成静态数据 |
| 接续 / 接手 | Resume / Take over | 新环境或新模型基于快照继续任务 |
| 双格式同步 | Dual-format sync | Markdown 与 JSON 描述同一份状态，改一处同步另一处 |

## 快照状态（status）枚举

| 值 | 中文 | 含义 |
|---|---|---|
| `initialized` | 已初始化 | 任务开启前，只有目标/约束/背景 |
| `in-progress` | 进行中 | 任务正在执行 |
| `checkpointed` | 已打点 | 任务过程中保存的断点快照 |
| `completed` | 已完成 | 任务已结束 |
| `abandoned` | 已放弃 | 任务不再继续 |
