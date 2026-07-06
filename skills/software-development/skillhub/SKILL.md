---
name: skillhub
description: SkillHub 第三方技能商店 — 搜索、安装、管理 AI 技能
category: software-development
trigger: skillhub, 技能商店, skillhub搜索, 安装技能, 搜索技能
frozen: false
---

# SkillHub 技能商店

SkillHub (skillhub.cn) 是一个第三方 AI 技能商店，提供社区分享的各种智能体技能。

## 前置条件

- Python 3.x 可用
- `skillhub` CLI 已安装（`~/.local/bin/skillhub`）
- 核心脚本：`~/.skillhub/skills_store_cli.py`

## 常用命令

### 搜索技能

```bash
skillhub search <关键词>
```

示例：
```bash
skillhub search calendar        # 搜索日历相关技能
skillhub search git             # 搜索 Git 相关技能
skillhub search react           # 搜索 React 相关技能
```

### 安装技能

```bash
skillhub install <slug>
```

安装到当前目录的 `./skills/` 下。

### 查看已安装的技能

```bash
skillhub list
```

### 升级技能

```bash
skillhub upgrade
```

### 登录

```bash
skillhub login                  # 社区 token 登录
skillhub login --api-key <key>  # 企业 API key 登录
```

## 使用流程

1. 用户说"帮我找个 xxx 技能"
2. 同时搜索两个商店：
   - `npx skills find xxx`（Vercel 商店）
   - `skillhub search xxx`（SkillHub 商店）
3. 汇总结果给用户选择
4. 用户确认后安装

## 安装后注册到 Hermes（统一技能目录）

所有第三方技能**统一安装到 Hermes 技能目录**，这样 `skills_list` 和 `skill_view` 都能直接识别：

```bash
# 安装技能（skillhub 强制装到当前目录的 ./skills/ 下）
skillhub install <slug>

# 移动到 Hermes 统一技能目录（不保留源目录）
SKILL_NAME="<slug>"
HERMES_SKILLS_DIR="/c/Users/dtyao/AppData/Local/hermes/skills"
mv "./skills/$SKILL_NAME" "$HERMES_SKILLS_DIR/software-development/$SKILL_NAME"
```

## 注意事项

- `skillhub` 安装技能到**当前目录**的 `./skills/` 下
- 安装后复制到 `C:\Users\dtyao\AppData\Local\hermes\skills\software-development\` 下统一管理
- SkillHub 需要登录才能安装某些技能（社区 token 或企业 API key）
- 搜索不需要登录
