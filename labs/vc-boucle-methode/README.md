# Review an agent's changes against a specification and its tests

Level 1 lab of the course **Governing and Securing AI-Generated
Applications**, track "Vibe coding with a method". A coding agent proposes
two patches to the order module of the portail-achats. One meets the
specification. The other keeps the suite green by switching off the test it
breaks. You apply the first, refuse the second with a written reason, and
tie the new requirement to a test that would catch its regression.

| | |
|---|---|
| Target | your machine: Python 3.11 or later, pytest, `patch` or git. No network, no AI service, no API key |
| Duration | about 40 minutes |
| Paired lesson | [The work loop](https://www.stephane-robert.info/en/docs/ai/ai-generated-applications/work-loop/) |
| Next | `vc-paquet-inexistant` |

```bash
dsoxlab run vc-boucle-methode
cd labs/vc-boucle-methode/challenge/work
pytest -v
dsoxlab check vc-boucle-methode
```

## What you will be able to do

- Read an agent's patch for what it does, not for what its message says.
- Tell a green suite from a suite where every test ran.
- Record a refusal precisely enough for its author to act on it.
- Tie a requirement to a test that fails when the requirement is broken.
