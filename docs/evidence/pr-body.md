# README delivery

Before: 60/100. After: 100/100.

![Before desktop](https://github.com/user-attachments/assets/79ae5ea1-302f-48e7-abd8-32a76143ff4b)

![Before desktop-dark](https://github.com/user-attachments/assets/929fcf7d-c414-42f9-96b5-6aa3df447eed)

![Before mobile](https://github.com/user-attachments/assets/4ed56a04-a403-48a2-9270-6db122a33dc6)

![After desktop](https://github.com/user-attachments/assets/68b9eca0-2a7e-4ed3-ac89-84db0a575eae)

![After desktop-dark](https://github.com/user-attachments/assets/00da3c91-5472-435e-9feb-a5db39e1aeea)

![After mobile](https://github.com/user-attachments/assets/984947ca-b30b-4b5e-bba2-6afcb34123a4)

## Verification

| Check | Status | Evidence |
|---|---|---|
| V1 | pass | Passed |
| V2 | pass | Passed |
| V3 | pass | Passed |
| V4 | pass | Passed |
| V5 | pass | Passed |
| V6 | pass | Passed |
| V7 | pass | Passed |
| V8 | skip | No test command discovered |
| V9 | pass | Passed |

## Stranger

{
  "status": "pass",
  "checks": {
    "what": true,
    "forWhom": true,
    "firstCommand": true,
    "wouldTry": true
  },
  "answers": {
    "what": "An agent skill called style-polish that builds a local writing-style profile and helps polish drafts in the writer’s own voice, with privacy filtering.",
    "forWhom": "Chinese writers who use a skill-capable AI agent and want drafts polished without losing their voice.",
    "firstCommand": "gh repo clone bmdy6/skill-style-polish .agents/skills/style-polish",
    "wouldTry": "yes",
    "why": "Preserving my voice with a local style profile sounds useful, and the quick start gives a concrete command and prompt.",
    "confusing": [
      "Which agents support this skill, and where should I run the clone command?",
      "What writing samples are needed to build the profile?",
      "Does local mean my drafts stay on my machine, or can the agent send them to a model provider?",
      "The prominent leak-check result demonstrates a synthetic privacy check rather than the quality of an actual rewrite.",
      "The page targets Chinese writers but shows English instructions and no Chinese before-and-after example."
    ]
  }
}

## Images

- hero-light.png: fixture; self-check pass
- hero-dark.png: fixture; self-check pass
- hero-light.zh-CN.png: fixture; self-check pass
- hero-dark.zh-CN.png: fixture; self-check pass
- workflow-light.png: illustration; self-check pass
- workflow-dark.png: illustration; self-check pass
- workflow-light.zh-CN.png: illustration; self-check pass
- workflow-dark.zh-CN.png: illustration; self-check pass

## Gates

G1: agent. G2: agent.

{
  "G1": {
    "decidedBy": "agent",
    "choice": "Local Chinese writing style",
    "reason": "Noninteractive acceptance authorized by issue #1."
  },
  "G2": {
    "decidedBy": "agent",
    "choice": "Approved after screenshot inspection",
    "reason": "Desktop light/dark show the entire command and hero; mobile recorded. Fixed dark code contrast before approval."
  }
}

## Not verified

- V8: skip; No test command discovered
- External links only checked when --online was requested.
- Renderer: github-api.
