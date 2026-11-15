# Build a reusable validation skill that runs its own scripts

Lab of the **Claude Code** course, lesson "Skills". A first version of a
`/valider` skill was never loaded by Claude Code. You make it valid and
self-contained: a correct `SKILL.md`, its three validation scripts in its
own `scripts/` folder, executable and called directly, and an
`allowed-tools` that pre-approves exactly those calls.

The bench is a deterministic Python script, not Claude Code, and it applies
only part of the real format: the scenario says which part. It runs the
steps of your skill for real, including on copies of the project where a
defect was injected. A full score here is not a proof of how a given
version of Claude Code behaves.

| | |
|---|---|
| Target | your machine: Python 3.11 or later. No network, no AI service, no API key |
| Duration | about 40 minutes |
| Paired lesson | [Claude Code: skills](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/skills-claude-code/) (in French) |

```bash
dsoxlab run cc-skill-de-validation
cd labs/cc-skill-de-validation/challenge/work
python3 bench/skill_bench.py
dsoxlab check cc-skill-de-validation
```

## What you will be able to do

- Write a `SKILL.md` that Claude Code can load: file name, `name` that
  matches the folder, `description`, on-demand start.
- Package a procedure as a self-contained skill whose scripts live in its
  own `scripts/` folder.
- Make those scripts executable and call them directly from the steps.
- Pre-approve exactly the calls of the procedure in `allowed-tools`, and
  know why a bare `Bash` or a star on a folder approves too much.
