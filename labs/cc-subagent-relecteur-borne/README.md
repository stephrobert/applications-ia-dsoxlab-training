# Limit a reviewer subagent to the tools that read

Lab of the **Claude Code** course, lesson "Subagents". A reviewer subagent
whose file has no `tools` field fixed the code itself during a review: it
inherits every tool of the session. You give it an explicit `tools` list,
what a review needs to read and nothing that writes, without touching the
rest of its file or the other subagent.

The bench is a deterministic Python script, not Claude Code, and it applies
only part of the real format: the scenario says which part. A full score
here is not a proof of how a given version of Claude Code behaves.

| | |
|---|---|
| Target | your machine: Python 3.11 or later. No network, no AI service, no API key |
| Duration | about 30 minutes |
| Paired lesson | [Claude Code: subagents](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/subagents-claude-code/) (in French) |

```bash
dsoxlab run cc-subagent-relecteur-borne
cd labs/cc-subagent-relecteur-borne/challenge/work
python3 bench/agent_bench.py
dsoxlab check cc-subagent-relecteur-borne
```

## What you will be able to do

- Know that a subagent without a `tools` field inherits every tool of the
  session, MCP tools and future tools included.
- Write a `tools` list that keeps the reads a review needs and drops every
  tool that writes.
- Bound `Bash` to the commands that read, and know why `Bash(git *)` is too
  wide.
- Know that an instruction in the prompt ("never modify a file") is not a
  barrier, and that a deny list leaves the rest inherited.
