# style-polish

Help Chinese writers polish drafts in their own voice with a local, privacy-filtered agent skill.

[简体中文](README.zh-CN.md) · [MIT](LICENSE)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/hero-dark.png">
  <img src="docs/readme/hero-light.png" alt="An agent request beside actual command output" width="838">
</picture>

Real check on a synthetic example profile; the workflow is an illustration.

## Quick start

```sh
gh repo clone bmdy6/skill-style-polish .agents/skills/style-polish
```

Then tell your agent:

> Build my local style profile, then polish this draft in my voice.

Requires authenticated gh access to clone, Python 3.9+, and a skill-capable agent; standard library only.

## What you get

- **Privacy filtering.** Entities marked for review or redaction are filtered before profiling.
- **Personal style.** Profiles keep statistics and whitelisted language patterns.
- **Measurable feedback.** Draft checks score differences from the profile.

## How it works

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/workflow-dark.png">
  <img src="docs/readme/workflow-light.png" alt="An illustration of the three-step workflow" width="838">
</picture>

## Options

| Option | Purpose |
|---|---|
| `--no-llm` | Redact review-band entities automatically. |
| `--profile-out` | Choose the local profile path. |
| `--leak-gate` | Check profiles for leaks. |

See the [usage reference](docs/reference.md).

## FAQ and boundaries

**Are chats uploaded?** Scripts process files locally; keep corpora and personal profiles out of commits.

**Does it work in English?** Profiles and checks currently focus on Chinese; English results need separate validation.

**Is the image real personal data?** No; it shows an actual leak check on the repository's synthetic example profile.

**What was tested?** The pipeline ran in an empty temporary home, plus the synthetic profile check; real personal sessions were not accessed, and no automated test command exists.

<details><summary>Privacy boundary</summary>

Process only your own authorized material and review filtering results. Automated checks cannot prove the absence of every privacy risk.

</details>

## Contributing

Reproduce issues with synthetic data before submitting an issue or PR.

## License

[MIT](LICENSE).
