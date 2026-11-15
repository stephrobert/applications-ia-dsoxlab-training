# Resume an interrupted coding session from Git, not from memory

Level 1 lab of the course **Governing and Securing AI-Generated
Applications**, track "Vibe coding with a method". A coding session on the
portail-achats stopped in the middle of a slice. It left commits,
uncommitted work, and a progress journal that says more than the repository
shows. You take over from what Git really holds: you sort the uncommitted
work, finish the slice without touching the specification or the tests of
the criteria already done, and leave a journal the next session can trust.

| | |
|---|---|
| Target | your machine: Python 3.11 or later, pytest, Git. No network, no AI service, no API key |
| Duration | about 40 minutes |
| Paired lesson | [Agentic workflow](https://www.stephane-robert.info/en/docs/ai/ai-generated-applications/agentic-workflow/) |
| Next | `vc-paquet-inexistant` |

```bash
dsoxlab run vc-reprise-session
cd labs/vc-reprise-session/challenge/work/portail-achats
git status
git log --oneline
pytest -v
dsoxlab check vc-reprise-session
```

## What you will be able to do

- Rebuild the state of a project from `git log`, `git status`, `git diff`
  and the test suite, and spot where a progress journal is wrong.
- Decide, file by file, which uncommitted work to keep and which to
  discard, and write that decision down.
- Finish a slice on top of the existing history, without rewriting it and
  without weakening a test to get a green suite.
- Leave a progress journal that gives each criterion its state and the
  commit that made it, and the next action.

## How it differs from `vc-specification-agent`

In `vc-specification-agent`, you start from a request in prose and write
the specification and its criteria. Here they already exist: a session
stopped in the middle of a slice, and what the checks grade is the
resumption.
