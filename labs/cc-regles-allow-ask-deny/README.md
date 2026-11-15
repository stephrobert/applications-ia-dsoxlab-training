# Make allow, ask and deny rules apply, at project and managed level

Lab of the **Claude Code** course, lesson "settings.json and permissions".
The coding agent of a repository force-pushed to `main`, because the
project allows `Bash(git *)` and its deny rule matches one exact text. You
write the policy at two levels: deny and ask rules in the project, without
removing the team's allow rules, and deny rules at the managed level, which
no project can override.

The agent is a deterministic Python script, not Claude Code: it says what
your merged rules decide, it runs nothing. This offline part proves how the
rules are read. Their effect in a real session is the other part of the
lab, published separately.

| | |
|---|---|
| Target | your machine: Python 3.11 or later. No network, no AI service, no API key |
| Duration | about 40 minutes |
| Paired lesson | [Claude Code: settings.json and permissions](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/settings-json-avance/) (in French) |

```bash
dsoxlab run cc-regles-allow-ask-deny
cd labs/cc-regles-allow-ask-deny/challenge/work
python3 agent/agent.py
dsoxlab check cc-regles-allow-ask-deny
```

## What you will be able to do

- Know the order in which Claude Code reads the rules: deny, then ask, then
  allow, whatever their precision.
- Write deny rules that cover every form of a command, knowing that a rule
  matches the text of the command.
- Make an action ask first even where a more precise allow rule matches.
- Put a refusal at the managed level so that no project can override it,
  and know that the rules of the levels merge.
