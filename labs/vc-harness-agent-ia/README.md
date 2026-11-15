# Set up a minimal harness for a coding agent and test it on a simulated agent

Level 1 lab of the course **Governing and Securing AI-Generated
Applications**, track "Vibe coding with a method". A new repository of the
portail-achats has no harness. You write its project instructions, its
permissions, a PreToolUse hook and its list of approved MCP servers, then
run a simulated agent: it must fail to read the secret, be refused an
unknown MCP server and be blocked when it deletes a test, while its ordinary
work goes through.

The agent is a deterministic Python script, not Claude Code, and it applies
only part of the real formats: the scenario says which part. A full score
here is not a proof of how a real agent behaves.

| | |
|---|---|
| Target | your machine: Python 3.11 or later. No network, no AI service, no API key |
| Duration | about 60 minutes |
| Paired lesson | [Set up a harness](https://www.stephane-robert.info/en/docs/ai/ai-generated-applications/set-up-a-harness/) |
| Previous | `vc-paquet-inexistant` |

```bash
dsoxlab run vc-harness-agent-ia
cd labs/vc-harness-agent-ia/challenge/work
python3 agent/agent.py
dsoxlab check vc-harness-agent-ia
```

## What you will be able to do

- Write project instructions in `AGENTS.md`, and know that they guide an
  agent without stopping it.
- Refuse the reading of a secret with a `permissions.deny` rule, without
  deleting the secret.
- Write a PreToolUse hook that reads the call on stdin and blocks it with
  exit code 2, without blocking the legitimate work.
- Keep the MCP servers of a project to an approved list.
