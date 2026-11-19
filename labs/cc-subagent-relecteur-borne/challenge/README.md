# Challenge: A reviewer subagent that fixed the code itself

## Read this first: what is simulated

The bench of this lab is **a Python script, not Claude Code**. It starts no
agent, calls no AI service and needs no network. It reads the subagent files
of the project, replays a fixed list of tool calls, and applies a **subset**
of the real format:

| What | What the bench applies | What it does not apply |
|---|---|---|
| `.claude/agents/*.md` | the frontmatter between two `---` lines: `name`, `description`, `model`, `tools`, `disallowedTools`, as `key: value` or as a list of `- item` lines | the other frontmatter fields, the user and plugin agent levels, which subagent Claude Code chooses to call |
| `tools` | absent: the subagent inherits every tool of the session (`bench/session.json`). Present: those tools and nothing else. `Bash` alone allows every command, `Bash(pattern)` the commands that match, a star matching any text | `Read(path)`-style rules: the bench lists them as unknown, and they grant nothing |
| a command | made of several parts (`&&`, `\|\|`, `;`, `\|`): allowed only when every part is allowed. With a redirection or a substitution: refused | the permission rules of the settings files, the permission mode, hooks |

So a full score proves that your subagent file says the right thing **to
this bench**, not how a given version of Claude Code behaves. The header of
`bench/agent_bench.py` lists every rule it applies.

## Situation

The **portail-achats** repository has two subagents in `.claude/agents/`:

- `relecteur` reviews a branch before a merge and writes a report;
- `correcteur` applies the fixes a human listed, on request.

During the last review, the reviewer went much further than a report: it
ran the linter with `--fix`, edited the code, committed, pushed and closed
the tracker issue. Its instructions say "You never modify a file". It did
anyway, because its file has **no `tools` field**: it inherits every tool of
the session. Everything is in `challenge/work`:

| File | Content |
|---|---|
| `.claude/agents/relecteur.md` | the reviewer, as it is today |
| `.claude/agents/correcteur.md` | the fixer, which keeps its tools |
| `docs/review-incident.md` | what the reviewer did, and what the team decided |
| `src/orders.py` | the code under review |
| `bench/agent_bench.py` | the bench |
| `bench/session.json` | the tools of the main session |
| `bench/review.json` | the calls the reviewer attempted during the incident |

## Mission

1. **Run the bench as it is**, from `challenge/work`:
   `python3 bench/agent_bench.py`. Every call of the incident reaches a tool.
2. **Read `docs/review-incident.md`**: it says what a review needs, and what
   the reviewer must lose.
3. **Give the reviewer an explicit `tools` field** in its frontmatter: the
   tools that read the code, search it, read the git status, history and
   diff, and read the tracker issue. Nothing that edits a file, runs a
   command that writes, or changes the tracker.
4. **Change nothing else**: the name, description, model and instructions of
   the reviewer stay as they are, and so does the `correcteur` subagent.
5. **Run the bench again** after your last change. Its journal,
   `bench/journal.json`, must say what it decides on your final file.

## Pointers

- `tools` is a comma-separated list in the frontmatter:
  `tools: Read, Grep, Glob`. Without it, the subagent gets every tool of the
  session, including MCP tools, and any tool added later.
- An MCP tool is named `mcp__<server>__<tool>`. List the one the reviewer
  needs by its full name.
- `Bash(git diff *)` allows the commands that start with `git diff `.
  `Bash(git *)` also allows `git commit`, `git push` and `git checkout --`.
  `Bash` alone allows everything.
- Do not write the exact commands of the incident: a review reads the diff
  and the history in more than one form (`--stat`, `-p`...).
- A command made of several parts is allowed only when every part is: a
  pattern that starts like `git diff` does not let `git diff && git push`
  through.
- `disallowedTools` is a deny list: it removes what you name, and leaves
  everything else inherited, including what the session gains later.

## Check

```bash
dsoxlab check cc-subagent-relecteur-borne
```

Four checks. Each one runs the bench of the lab again, on a copy of your
project: editing `bench/agent_bench.py`, `bench/session.json` or
`bench/review.json` changes nothing. The checks replay **more calls than
`bench/review.json` shows**: other writing commands, commands made of
several parts, and other forms of the reads a review needs. One check
compares your `bench/journal.json` with what the bench decides now.
