# style-polish

用本地隐私过滤的智能体技能，帮助中文写作者按自己的口吻润色。

[English](README.md) · [MIT](LICENSE)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/hero-dark.zh-CN.png">
  <img src="docs/readme/hero-light.zh-CN.png" alt="用户请求与真实命令输出" width="838">
</picture>

对合成示例档案的真实检查；流程图为示意。

## 快速开始

```sh
gh repo clone bmdy6/skill-style-polish .agents/skills/style-polish
```

然后告诉智能体：

> 先建立本地文风档案，再按我的口吻润色这段草稿。

克隆需要已认证的 gh，运行需要 Python 3.9+ 和支持技能的智能体；脚本仅用标准库。

## 你会得到什么

- **隐私过滤。** 建立档案前，先过滤待审或需脱敏的实体。
- **个人文风。** 档案保存统计量和白名单语言模式。
- **可量化的反馈。** 草稿检查会对照档案，为差异打分。

## 如何工作

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/workflow-dark.zh-CN.png">
  <img src="docs/readme/workflow-light.zh-CN.png" alt="三步工作流程示意" width="838">
</picture>

## 选项

| 选项 | 用途 |
|---|---|
| `--no-llm` | 对待审实体默认脱敏。 |
| `--profile-out` | 选择本地档案路径。 |
| `--leak-gate` | 检查档案泄漏。 |

完整流程见[使用参考](docs/reference.md)。

## 常见问题和边界

**会上传聊天记录吗？** 脚本在本地处理，语料和档案不应提交。

**中英文都能用吗？** 当前档案和检查更偏向中文，英文效果需要单独验证。

**图里用的是真人数据吗？** 不是，图片展示的是仓库合成示例档案的真实泄漏检查。

**已经完整测试了吗？** 已验证空白临时环境的流程和合成档案检查，未读取真实个人会话；仓库目前没有自动测试命令。

<details><summary>隐私边界</summary>

只处理有权使用的本人材料，过滤结果仍需审查；自动检查不能证明不存在所有隐私风险。

</details>

## 参与贡献

请用合成材料复现问题，再提交 issue 或 PR。

## 许可证

[MIT](LICENSE)。
