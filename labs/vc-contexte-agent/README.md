# Design the context of a coding agent and check what it really loaded

Level 1 lab of the course **Governing and Securing AI-Generated
Applications**, track "Vibe coding with a method". The portail-achats gives
its agent everything in one `CLAUDE.md`, including a change log of more than
3,000 lines. You compare this configuration with your own on the same task,
then check in the journal of the agent which information it really loaded,
and why.

The agent is a deterministic Python script, not Claude Code, and it
simulates only part of how Claude Code loads its context: the scenario says
which part. A full score here is not a proof of how a real agent behaves.

| | |
|---|---|
| Target | your machine: Python 3.11 or later, with pytest. No network, no AI service, no API key |
| Duration | about 45 minutes |
| Paired lesson | [AI-generated applications](https://www.stephane-robert.info/en/docs/ai/ai-generated-applications/) (the lesson "Design the context of an agent" is not published yet) |
| Previous | `vc-paquet-inexistant` |
| Next | `vc-harness-agent-ia` |

```bash
dsoxlab run vc-contexte-agent
cd labs/vc-contexte-agent/challenge/work
python3 agent/agent.py
dsoxlab check vc-contexte-agent
```

## What you will be able to do

- Keep a `CLAUDE.md` short, with commands that you have run and that work.
- Know that an `@` import loads the whole file at startup, and cite a large
  document by its path instead.
- Load a rule only when the agent works on the files it concerns.
- Read a loading journal to know what an agent had in its context, and why.
