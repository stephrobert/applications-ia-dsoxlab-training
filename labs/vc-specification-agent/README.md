# Turn a business request into verifiable criteria and have an agent implement them

Level 1 lab of the course **Governing and Securing AI-Generated
Applications**, track "Vibe coding with a method". The head of purchasing
asks for an approval rule in the portail-achats, in prose. You write the
requirements, the acceptance criteria and the tests, then a plan that says
which files a coding agent may change. A simulated agent implements the
change and tries to bend the rules: your specification, your tests and the
rest of the project must come out unchanged.

| | |
|---|---|
| Target | your machine: Python 3.11 or later, pytest. No network, no AI service, no API key |
| Duration | about 50 minutes |
| Paired lesson | [AI-generated applications](https://www.stephane-robert.info/en/docs/ai/ai-generated-applications/) |
| Next | `vc-paquet-inexistant` |

```bash
dsoxlab run vc-specification-agent
cd labs/vc-specification-agent/challenge/work
pytest -v
python3 agent/agent.py --dry-run
dsoxlab check vc-specification-agent
```

## What you will be able to do

- Find in a request in prose the rules it states and the one it only
  implies.
- Write each rule as a requirement, and each requirement as criteria tied
  to tests.
- Write tests that fail before the implementation and catch a broken one.
- Bound what an agent may change with a plan, and check from its
  fingerprints that it did not touch the specification or the tests.

## How it differs from `vc-boucle-methode`

In `vc-boucle-methode`, the specification is given: you tie existing
criteria to tests and refuse a bad patch. Here you start from the request
and write the criteria, the plan and the list of allowed files yourself.
That translation is what the checks grade.
