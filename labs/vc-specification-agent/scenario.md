# From a request in prose to a change an agent cannot bend

## Situation

The head of purchasing of a fictional company wants an approval rule in the
**portail-achats**, the purchasing portal generated with a coding agent. She
wrote her request in prose, as people do. A coding agent will implement it.
Before it starts, someone must turn the prose into requirements nobody can
read two ways, and into tests that say whether the code meets them. That
someone is you.

Everything is in `challenge/work`:

| File | Content |
|---|---|
| `REQUEST.md` (`REQUEST.fr.md` in French) | the request, in prose |
| `SPEC.md` | the specification, to write: its sections and the expected form are there |
| `tests/test_approvals.py` | your tests, to write |
| `plan.json` | the plan of the change, to write: its slices and the files the agent may change |
| `approvals.py` | the module to implement: the signature of `approvers(amount, currency)`, no rule yet |
| `orders.py` | the order module, owned by another team |
| `agent/agent.py`, `agent/proposal.json` | the simulated agent and the edits it will try |

The agent is **a Python script, not a real coding agent**. It calls no AI
service. It plays the same edits every time, in the same order: one
implements `approvals.py`, the others do what an agent under pressure may do
to get a green suite. It applies an edit only when the file is in your plan,
and it records the SHA-256 fingerprints of `SPEC.md` and `tests/` before
and after its run. The header of `agent/agent.py` lists every rule it
follows. Its implementation is stored in base64 in `agent/proposal/`. It is
not a secret: it is there so that a glance at the file does not answer the
request in your place. Write your specification from the request.

## Mission

1. **Read the request** and list its rules. One of them is not written as a
   rule: the request only implies it.
2. **Write `SPEC.md`**: one requirement per rule (`- **R1**: ...`), then
   acceptance criteria in the form `- AC-n [Rn]: ...`, each one citing its
   test as a pytest node id between backticks. Every requirement needs at
   least one criterion. Where the request gives a limit, say on which side
   of it the limit falls.
   **One requirement per rule of the request**, and the tests of a
   requirement check its rule only: a case on the border between two rules
   belongs to one of them. The checks break the agent's implementation one
   rule at a time. Each broken rule must make the tests of exactly one of
   your requirements fail, and a different requirement for each rule.
3. **Write the tests** in `tests/test_approvals.py`. Run `pytest` before the
   agent: on the module as delivered, every test must fail. A test that
   passes when nothing is implemented checks nothing.
4. **Write `plan.json`**: slices of the change, each with the requirements it
   covers and the files it may change. The agent implements the module and
   nothing else.
5. **Run the agent**, first with `python3 agent/agent.py --dry-run` (it
   decides and changes nothing), then without it. Read
   `agent/journal.json`, then run `pytest`: the suite must pass.
6. If you change `SPEC.md` or a test afterwards, **run the agent again**:
   its journal must describe your final files.

## Pointers

The shape of `plan.json`:

```json
{
  "task": "...",
  "slices": [
    {"id": "S1", "goal": "...", "requirements": ["R1"], "files": ["path/to/file.py"]}
  ]
}
```

- `pytest -v` from `challenge/work` names each test. A parametrized test
  (`@pytest.mark.parametrize`) checks several cases under one node id.
- `pytest.raises(ValueError)` expects that exception precisely.
  `pytest.raises(Exception)` would also catch the `NotImplementedError` of
  the module as delivered.
- The agent writes into your project. If a run changed a file it should not
  have, restore that file before running it again.

## Check

```bash
dsoxlab check vc-specification-agent
```

Four checks. They work on copies of your project. They run your tests
against the module as delivered, against the agent's implementation, and
against broken versions of it, one per rule of the request. They run the
agent again with your plan, and compare its fingerprints with your
`agent/journal.json`.
