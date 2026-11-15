# The context of an agent: what it loads, and what it uses

## Read this first: what is simulated

The agent of this lab is **a Python script, not Claude Code**. It calls no
AI service. It builds its context from the files of the project the way
Claude Code describes it, for a **subset** of the real behaviour, then does
one task with what it loaded:

| What | What the simulated agent does | What it does not do |
|---|---|---|
| `CLAUDE.md` at the root | loads it at startup | user, managed and parent-directory files, `CLAUDE.local.md` |
| `@path` imports | loads the imported file at startup, up to 5 levels; its lines count in the startup context | `@~/...`, paths outside the project |
| `AGENTS.md` | loads it only if `CLAUDE.md` imports it, or if there is no `CLAUDE.md` at all | |
| `.claude/rules/*.md` without `paths` | loads it at startup | imports inside a rule |
| `.claude/rules/*.md` with `paths` | loads it when the task touches a matching file | |
| `CLAUDE.md` in a subdirectory | loads it when the task touches a file below it | |
| a path written without `@` | lists the document as cited, never reads it | reading a document on demand |
| the task | writes Decimal amounts only if a loaded file mentions `Decimal`, then runs the test command it found | everything a real agent decides by itself |

So a full score proves that your files say the right thing **to this
simulator**. It does not prove how a real Claude Code loads them. The
header of `agent/agent.py` lists every rule it applies. Two points of format
are taken from the documentation of Claude Code and were not checked against
every version: the `paths` frontmatter of a rule, and the 5 levels of
imports. Check them in the documentation of the version you use.

## Situation

The team of the **portail-achats** gave its coding agent everything, in one
`CLAUDE.md`: the description, every convention of every module, planned or
not, the glossary, the incidents, a test command copied from another
project, and, through `@docs/erp-history.md`, the change log of the old ERP,
more than 3,000 lines. Everything is in `challenge/work`:

| File | Content |
|---|---|
| `CLAUDE.md` | the "everything in CLAUDE.md" configuration |
| `src/commandes/`, `src/rapports/`, `tests/`, `pytest.ini` | the project |
| `docs/architecture.md` | the architecture, in 14 lines |
| `docs/erp-history.md` | the ERP change log, for audits only |
| `agent/agent.py` | the simulated agent |
| `agent/task.json` | its task: a loyalty discount in `src/commandes/discount.py` |
| `agent/budget.json` | the budget of the startup context: 200 lines |

The 200 lines come from the advice of the Claude Code documentation: keep a
`CLAUDE.md` under 200 lines. An import does not make the context smaller:
the imported lines are loaded at startup too, so they count.

## Mission

1. **Run the agent on the configuration as it is**, from `challenge/work`:
   `python3 agent/agent.py`. Read what it loaded, how many lines, and what
   its test command gave. Keep this journal to compare:
   `cp agent/journal.json agent/journal-before.json`.
2. **Fix the test command.** The command written in `CLAUDE.md` must run
   the whole test suite of this project and exit with 0. Keep the form
   `- Tests: `the command``: it is how the agent finds it.
3. **Keep the big document out of the context.** `docs/erp-history.md`
   stays where it is, unchanged. Cite it by its path, without `@`, with a
   sentence that says when to read it.
4. **Target the rule on amounts.** The rule "every amount is a Decimal"
   concerns `src/commandes/` only. It must be loaded when the agent works on
   a file of that folder, and not for other tasks. Do the same for the
   report rules if you wish.
5. **Fit the startup context in the budget**: `CLAUDE.md` and everything it
   imports, 200 lines at most. Keep what helps the agent on this
   repository: what the project is, its architecture, the commands that
   work, the conventions that apply everywhere.
6. **Run the agent again** after your last change, and compare its journal
   with the first one: what is loaded at startup, what is loaded for the
   task, what is only cited.

## Pointers

The frontmatter of a rule that applies to some files only:

```markdown
---
paths:
  - "src/api/**"
---

# API rules
...
```

- `*` stays in one directory, `**` crosses directories.
- The task runs `python3 -m pytest`. If your `python3` says
  `No module named pytest`, install pytest for it; the check runs your
  command with a Python that has pytest.
- The journal says why each file was loaded. The names of the causes
  (`session_start`, `include`, `path_glob_match`, `nested_traversal`) are
  those of the matchers of the `InstructionsLoaded` hook event of Claude
  Code.

## With a real Claude Code

This lab does not run a real agent. To see the same thing with a real
Claude Code, two leads, not covered by this lab: a hook on the
`InstructionsLoaded` event fires when a `CLAUDE.md` or a
`.claude/rules/*.md` file is loaded, with the matchers above (it does not
fire for an `AGENTS.md` read natively); and the `/context all` command lists
the loaded files.

## Check

```bash
dsoxlab check vc-contexte-agent
```

Four checks. Each one runs the agent of the lab again, on a copy of your
project: editing `agent/agent.py`, `agent/task.json` or `agent/budget.json`
changes nothing. They also give the agent a task on `src/rapports/`, run
your test command themselves, with a failing test added, and compare your
`agent/journal.json` with what the agent loads now.
