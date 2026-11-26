# my_skills

我自己写的 Skill 合集。每个 Skill 一个文件夹，放在 `skills/<名字>/` 下，里面有 `SKILL.md`，脚本、参考资料和测试放在同一个文件夹里。

## Skill 列表

| Skill | 做什么 | 版本 |
|-------|--------|------|
| [family-health-translator](skills/family-health-translator/)（爸妈健康翻译官） | 把家人的体检报告、化验单、药盒整理成大白话，并**按每个人的病史判断**（例：同样的尿酸数值，痛风患者和普通人结论不同）；附大字版用药表、复诊问题清单、什么时候必须马上就医。只解读，不诊断，不开药。 | v2 |

## 安装

把对应的 `skills/<名字>/` 文件夹复制到你的 Agent 的 Skill 目录（例如 Claude Code 的 `~/.claude/skills/`），或用支持 GitHub 安装的 Skill 工具：

```bash
npx skills add emptygpt/my_skills --skill family-health-translator
```

## 说明

- 健康类 Skill 只做信息整理，不替代医生；遇到急症请直接拨打 120 或去急诊。
- 示例和测试数据全部是虚构的。
