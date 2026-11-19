# Challenge: A validation skill that Claude Code never loaded

## Read this first: what is simulated

The bench of this lab is **a Python script, not Claude Code**. It calls no
AI service and needs no network. It reads one skill of the project, checks a
**subset** of its format, then **runs** the commands its steps name:

| What | What the bench applies | What it does not apply |
|---|---|---|
| the file | `.claude/skills/<skill>/SKILL.md`, with that exact file name | the user and plugin skill levels, the `/name` menu |
| the frontmatter | `name` (lowercase letters, digits, hyphens, the folder name), `description` (not empty), `disable-model-invocation`, `allowed-tools` | `paths`, `user-invocable`, `argument-hint`, `$ARGUMENTS`, when Claude decides to load a skill |
| a step | a numbered line of the body that contains a code span: its first code span is the command | the summary Claude would write after the steps |
| `allowed-tools` | `Bash(pattern)`, a star matching any text. A step it does not cover is **not run**: Claude Code would ask you first, and the bench runs unattended | the permission rules of the settings files |
| running a step | from the project root, without a shell. A program given by a path must exist and be executable. Every step runs, even after a failure | |

So a full score proves that your skill says the right thing **to this
bench**, and that its scripts really run. It does not prove how a given
version of Claude Code loads it. The header of `bench/skill_bench.py` lists
every rule it applies.

## Situation

The **portail-achats** repository validates its code with three scripts
before every pull request: style, unit tests, secrets in the code. The CI
runs them directly, as programs. `docs/validation.md` gives their order and
their arguments.

Someone started a `/valider` skill so that Claude Code runs the same
procedure on demand. Claude Code never loaded it, and nobody ran it to the
end. Everything is in `challenge/work`:

| File | Content |
|---|---|
| `.claude/skills/valider/skill.md` | the first version of the skill |
| `docs/validation.md` | the procedure, and what the team decided for the skill |
| `tools/validation/` | the three scripts the CI runs |
| `src/`, `tests/` | the code and its unit tests |
| `bench/skill_bench.py` | the bench |

## Mission

1. **Run the bench as it is**, from `challenge/work`:
   `python3 bench/skill_bench.py`. Read why it does not see a skill.
2. **Make SKILL.md valid**: the file name, the `name`, a `description` that
   says when to use the skill, and an on-demand start only.
3. **Make the skill self-contained**: copy the three scripts, unchanged, into
   `.claude/skills/valider/scripts/`, and make them executable.
4. **Call them directly** in the steps, in the order and with the arguments
   of `docs/validation.md`, from the project root.
5. **Pre-approve exactly those three calls** in `allowed-tools`, and nothing
   else.
6. **Run the bench again** after your last change. Its journal,
   `bench/journal.json`, must show the three steps passed on your final
   files.

## Pointers

- A skill is a folder: `.claude/skills/<name>/SKILL.md`. The file name is
  `SKILL.md`, in capitals. The `name` is written in lowercase and matches
  the folder.
- `disable-model-invocation: true` keeps a skill for `/name` only: Claude
  does not start it on its own.
- `allowed-tools` takes entries separated by spaces:
  `Bash(path/to/script.py arg)`. A star matches any text, so a star on a
  folder approves every script that someone adds to it later.
- A script called directly (`path/to/script.py`) needs its first line
  (`#!/usr/bin/env python3`, already there) and the execute bit
  (`chmod +x`). Called as `python3 path/to/script.py`, it needs neither, and
  the CI does not call it that way.
- `cp` copies a file without its execute bit unless the source has one.
- The bench runs the steps for real: a script that prints "ok" without
  checking anything is caught.

## Check

```bash
dsoxlab check cc-skill-de-validation
```

Five checks. Each one runs the bench of the lab again, on a copy of your
project: editing `bench/skill_bench.py` changes nothing. One check runs your
skill on copies of the project where a defect was **injected** (a secret in
the code, a failing test, a line too long), and expects each defect to fail
the right step. Another one tries commands that no step uses, and expects
`allowed-tools` to approve none of them.
