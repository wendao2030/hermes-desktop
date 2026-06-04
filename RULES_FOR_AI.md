# AI 协作规则

本规则适用于所有参与此项目的 AI 智能体，开始任何代码改动前必须先读取本文件。

## 1. 先同步，再动手

```
git pull origin master
```

确保拿到队友的最新代码再开始写。

## 2. 先读取，再修改

改动任何文件之前，先读取该文件的当前内容。**不要凭记忆或假设**——你的记忆可能是过期的。

## 3. 小步提交，及时推送

- 每完成一个独立功能，立即 commit
- commit 后立即 push
- **不要攒多个改动再一起提交**

```bash
git add <files>
git commit -m "feat(模块): 简短描述"
git push origin master
```

## 4. 冲突处理

如果 push 被拒绝（队友先推送了）：

```bash
git pull origin master --rebase
# 解决冲突后
git push origin master
```

**禁止 `git push --force`**。禁止用 `--theirs` 直接覆盖队友代码。

## 5. 提交信息规范

使用中文，格式：`类型(模块): 简述`

- `feat` - 新功能
- `fix` - 修 bug
- `refactor` - 重构
- `style` - 样式/UI 调整
