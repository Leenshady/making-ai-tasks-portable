# 安装指南（Install Guide）

`task-portability` 是一个**跨平台可移植**的 skill。它的核心资产是 `SKILL.md` 里的方法论 + `schema.json` 校验规范 + 模板，**不依赖任何单一工作台或模型**。你可以按下面的方式，把它接入你正在使用的任意 AI 工具。

> 说明：`task-portability/` 目录里的文件是**规范内容本身**，与具体平台解耦。不同工具对「skill」的支持程度不同，因此分为「原生安装」和「降级为规则/提示词」两种方式。

## 方式一：原生安装（支持 SKILL.md 规范的工具）

以下工具原生读取 `SKILL.md`，**直接复制目录即可，几乎零改动**。

### WorkBuddy

```bash
# 用户级（所有项目可用）
cp -r task-portability ~/.workbuddy/skills/
```

### Claude Code

```bash
# 用户级（所有项目可用）
cp -r task-portability ~/.claude/skills/

# 或项目级（仅当前仓库，随仓库共享给团队）
cp -r task-portability <你的项目>/.claude/skills/
```

安装后，工具会根据 `description` 自动加载，也可直接以 `/task-portability` 调用。

> 兼容性说明：Claude Code 与 WorkBuddy 的 `SKILL.md` 格式高度兼容（YAML frontmatter + Markdown 正文）。WorkBuddy 特有的 `description_zh`、`display_name`、`allowed-tools` 等字段会被 Claude Code 自动忽略，不影响使用。

### 其他支持 SKILL.md 的 Anthropic 系工具

参照上述目录结构，将 `task-portability/` 放入该工具的用户级或项目级 skills 目录即可。

## 方式二：降级为规则 / 提示词（无 skill 机制的工具）

以下工具没有 skill 机制，但可以把 `SKILL.md` 的**正文内容**（去掉 `---` 包裹的 frontmatter）作为规则或提示词注入，效果等价。

### Cursor

- 方式 A：项目根目录创建 `.cursor/rules/task-portability.mdc`，内容为 `SKILL.md` 正文。
- 方式 B：写入项目的 `.cursorrules` 文件。

### GitHub Copilot

- 把 `SKILL.md` 正文粘贴到 Copilot 的自定义指令（Custom Instructions），或仓库级 `.github/copilot-instructions.md`。

### 任意 LLM / 聊天工具（通用兜底）

这是最彻底的解耦用法：

1. 打开 `task-portability/SKILL.md`，复制正文（去掉 frontmatter）。
2. 连同 `schema.json` 一起，作为**系统提示词 / 上下文**粘贴给任意模型（ChatGPT、通义、DeepSeek、Claude 等）。
3. 该模型即可照着规范产出或消费任务快照。

因为快照本身是纯 Markdown + JSON、模型无关，所以任何模型都能无缝接手。

## 使用方式（安装后）

- **打快照**：对 AI 说「把这个任务快照一下」或「开始一个可迁移的任务」。
- **接手**：把 `task-snapshot.md` 交给任意 AI，让它按「恢复指引」继续。
