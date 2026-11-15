# Test a hook that succeeds, blocks and crashes

First lab of the **Claude Code** section: one mechanism per lab. The hooks
of the portail-achats look fine and protect nothing: the guard crashes, the
style checker reports to nobody, the test run never stops the turn. You
replay them on a hook bench with fixed PreToolUse, PostToolUse and Stop
events, read their exit codes and what Claude would receive, then repair
them.

The bench is a Python script, not Claude Code. It really runs your hooks,
and simulates the events and what Claude Code does with an exit code and an
output. The scenario says exactly what is simulated.

| | |
|---|---|
| Target | your machine: Python 3.11 or later. No network, no Claude Code, no AI service, no API key |
| Duration | about 45 minutes |
| Paired lesson | [Claude Code hooks](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/hooks-claude-code/) (in French) |

```bash
dsoxlab run cc-hook-qui-echoue
cd labs/cc-hook-qui-echoue/challenge/work
python3 banc/banc_hooks.py
dsoxlab check cc-hook-qui-echoue
```

## What you will be able to do

- Read what exit codes 0, 1 and 2 of a hook do on PreToolUse, PostToolUse
  and Stop, and know that a hook that crashes (exit code 1) lets the action
  go on.
- Block a call with exit code 2 and a reason on stderr, without blocking the
  ordinary work.
- Send the report of a tool that writes on stdout to Claude, after an edit
  or at the end of a turn.
- Refuse a call with a JSON `permissionDecision` in exit code 0, at the
  right level of the JSON.
- Test a hook on its own, on the exact JSON it receives.
