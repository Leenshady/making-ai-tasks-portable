# 任务快照（示例）

> 这是一个示例快照，展示一份"合格"的任务快照长什么样。接手者读这一份即可完全接手。

## 身份与元信息

| 字段 | 值 |
|---|---|
| 任务 ID | `task-20261102-1530` |
| 标题 | 为 NDM 扩展调整下载拦截策略 |
| 状态 | in-progress |
| 创建时间 | 2026-11-02T14:00:00+08:00 |
| 更新时间 | 2026-11-02T15:30:00+08:00 |
| 快照版本 | 1.0.0 |

## 目标

**目标（Goal）**

在不影响扩展其他功能（下载管理、状态监控）的前提下，调整 NDM Chrome 扩展的下载拦截策略，使其支持按文件类型过滤。

**成功标准（Success Criteria）**

- `ct.js` 中新增文件类型过滤逻辑，且现有拦截路径行为不变
- 通过手工测试：MP4 类型被拦截、其他类型正常放行
- `bg.js` 无需改动（验证跨上下文通信不受影响）

**约束（Constraints）**

- 必须保持 MV3 架构，使用 `chrome.storage.session` + `chrome.sendMessage` 通信
- 不引入第三方库
- 不改变现有下载管理的 UI 与交互

**不做的事（Non-goals）**

- 不做下载速度/断点续传相关优化
- 不重构 `bg.js`

## 上下文与背景

**背景（Background）**

NDM 扩展采用 MV3 架构，`ct.js`（内容脚本）负责拦截下载链接，`bg.js`（Service Worker）负责网络监控与跨上下文通信。用户希望针对特定文件类型收紧拦截规则，但担心影响现有功能。

**关键决策（Key Decisions）**

- 决策：过滤逻辑放在 `ct.js` 而非 `bg.js` → 理由：拦截发生在内容脚本层，改动局部、风险可控，符合"不影响其他功能"的要求
- 决策：用 `chrome.storage.session` 缓存过滤规则 → 理由：MV3 下 Service Worker 可能休眠，session 存储是最可靠的跨上下文方案

**假设（Assumptions）**

- 假设当前版本 `ct.js` 的拦截入口集中在单一函数（尚未逐行确认）

**术语（Terminology）**

- `ct.js`：内容脚本，负责拦截下载链接
- `bg.js`：Service Worker，负责网络监控与跨上下文通信

## 进度

**已完成（Completed）**

- 梳理了 ct.js 与 bg.js 的职责划分与通信机制
- 定位到下载拦截的代码路径

**进行中（In Progress）**

- 正在分析 `ct.js` 中拦截函数的具体实现，逐行拆解

**下一步（Next Steps）**

1. [优先级 1] 确认 `ct.js` 中拦截入口函数的具体位置与行号
2. [优先级 2] 设计文件类型过滤的插入点
3. [优先级 3] 实现过滤逻辑并做最小化改动

**阻塞项（Blockers）**

- 无

**风险（Risks）**

- 过滤规则缓存键命名不当可能导致与现有 session 数据冲突 → 用独立命名空间规避

## 工件与依赖

**关键文件（Files）**

- `F:\dev\ndm-extension\ct.js` — 内容脚本，拦截下载链接，需在此新增过滤逻辑
- `F:\dev\ndm-extension\bg.js` — Service Worker，本次不改动
- `F:\dev\ndm-extension\manifest.json` — 扩展清单，若新增权限需同步

**外部依赖（Dependencies）**

- Chrome 浏览器（含 NDM 扩展，用于手工测试）

**运行环境（Environment）**

- Windows 11
- Chrome 最新稳定版（MV3 支持）

**关键命令（Commands）**

```bash
# 在 chrome://extensions 中重新加载扩展以应用改动
```

## 恢复指引（如何接手）

**如何接续（How to Resume）**

1. 打开 `F:\dev\ndm-extension\ct.js`，找到下载拦截入口函数（约在文件后半段）。
2. 从"下一步"的第一项开始：确认入口函数位置与行号。
3. 改动前先跑一遍现有拦截，确认基线行为。

**联系（Contact）**

任务发起者（可通过原对话/工作台联系）

**交接备注（Handoff Notes）**

- 用户偏好详细技术解释：回复需含架构图、逐行代码分解、文件路径与行号标注、方案对比表格。
- 通信机制上 `chrome.storage.session` 优于 `chrome.sendMessage`（MV3 可靠性更高），新代码沿用 session 方案。
