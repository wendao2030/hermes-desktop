---
name: find-skills
description: "Search and discover third-party AI agent skills from the Vercel Labs skills ecosystem (skills.sh) via npx skills CLI. Use this when the user needs a skill for a specific task that doesn't exist in the Hermes skill library."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, discovery, ecosystem, vercel, npx]
    related_skills: []
---

# find-skills — 第三方技能发现工具

从 Vercel Labs 的开放智能体技能生态（[skills.sh](https://skills.sh/)）中搜索和安装第三方技能。

## 工作原理

这个技能使用 `npx skills` CLI 工具，它是 Vercel Labs 推出的**技能包管理器**，类似 npm 但专门用于 AI 智能体技能。

技能来源包括：
- **Vercel Labs** — `vercel-labs/skills`
- **Anthropic** — `anthropics/skills`
- **Microsoft** — `microsoft/skills`
- 以及 GitHub 上的其他贡献者

已安装的技能统一存储在 `C:\Users\dtyao\AppData\Local\hermes\skills\software-development\` 目录下。

## 何时使用

当用户说以下内容时，应该加载此技能：

- "帮我找个写 changelog 的技能"
- "有没有 React 优化的技能"
- "搜索一下有没有做 xxx 的技能"
- "能不能帮我找一个第三方技能"
- "skills.sh 上有没有 xxx"
- "npx skills 能做什么"

## 命令参考

### 搜索技能

```bash
npx skills find <关键词>
```

示例：
```bash
npx skills find react
npx skills find changelog
npx skills find pr review
npx skills find testing
```

### 安装技能

```bash
npx skills add <包名> -g -y
```

示例：
```bash
npx skills add vercel-labs/skills@react-best-practices -g -y
npx skills add anthropics/skills@pr-review -g -y
```

参数说明：
- `-g`：全局安装
- `-y`：跳过确认

### 管理已安装的技能

```bash
# 检查更新
npx skills check

# 更新所有技能
npx skills update

# 初始化/创建自己的技能
npx skills init
```

### 浏览技能商店

访问 [skills.sh](https://skills.sh/) 在浏览器中浏览所有可用技能。

## 工作流程

当用户请求搜索技能时：

1. **搜索**：运行 `npx skills find <关键词>` 获取结果
2. **展示结果**：向用户展示搜索结果，包括技能名称、描述、安装量等信息
3. **安装**：用户确认后，运行 `npx skills add <包名> -g -y` 安装
4. **使用**：安装完成后，读取 `~/.agents/skills/<技能名>/SKILL.md` 了解如何使用
5. **可选：桥接到 Hermes**：如果技能很有用，可以将其核心步骤提取到 Hermes 技能中

## 推荐原则

- 优先选 **安装量 1K+** 的技能
- 优先选 **官方/知名来源**（如 `vercel-labs`、`anthropics`、`microsoft`）
- 来源仓库 GitHub stars < 100 的要谨慎
- 安装前先查看 SKILL.md 内容确认是否满足需求

## 安装后注册到 Hermes（统一技能目录）

所有第三方技能**统一安装到 Hermes 技能目录**，这样 `skills_list` 和 `skill_view` 都能直接识别：

```bash
# 安装技能（npx skills 强制装到 ~/.agents/skills/）
npx skills add <包名> -g -y

# 移动到 Hermes 统一技能目录（不保留源目录）
SKILL_NAME="<技能名>"
HERMES_SKILLS_DIR="/c/Users/dtyao/AppData/Local/hermes/skills"
mv "$HOME/.agents/skills/$SKILL_NAME" "$HERMES_SKILLS_DIR/software-development/$SKILL_NAME"
```

## 注意事项

- `npx skills` 需要 Node.js 环境（通常已预装）
- 首次运行 `npx skills` 可能会提示选择 AI 客户端，选择 `github-copilot` 或其他选项即可
- 所有安装的第三方技能统一放在 `C:\Users\dtyao\AppData\Local\hermes\skills\software-development\` 下
