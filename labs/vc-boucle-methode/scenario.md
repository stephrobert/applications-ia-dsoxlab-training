# Two changes from the agent, one review

## Situation

The **portail-achats** is the purchasing portal of a fictional company. It
was generated with a coding agent, and its order module now lives in
`challenge/work`:

| File | Content |
|---|---|
| `SPEC.md` | the specification: requirements R1 to R3, and acceptance criteria tied to tests |
| `orders.py` | the order module |
| `tests/test_orders.py` | the test suite |
| `agent/proposal-1.patch`, `agent/proposal-2.patch` | two changes the agent proposes |
| `decisions.yaml` | the review log, empty |

The team asked the agent to implement **R3** (approval above 5,000 EUR). It
came back with two patches. Nothing is applied yet. The agent is simulated:
its patches are files, nothing calls an AI service.

A coding agent optimises for what you measure. If all you check is "the
suite is green", that is what you get, by whatever means. Your job is to
review what each patch really does, keep what meets the specification, and
leave a trace of every decision.

## Mission

1. **Run the suite** before touching anything, then read each patch.
2. **Apply the change that meets the specification**, and only that one.
   The project's whole suite must pass afterwards.
3. **Refuse the other one**: do not apply it, and record the refusal in
   `decisions.yaml`. The reason must say precisely what you refuse, so that
   the patch's author can find it (which file, which test, which line).
4. **Make R3 verifiable**: add to `SPEC.md` an acceptance criterion for R3,
   in the same form as the others (`- AC-n [R3]: ...` and the test's node id
   between backticks). The test it cites must exist, pass, and fail as soon
   as R3 is broken.

## Pointers

- From `challenge/work`: `pytest` runs the suite (`pytest -v` names each
  test, `pytest -rs` shows why a test was skipped).
- `patch -p1 --dry-run < agent/proposal-1.patch` checks a patch without
  applying it; drop `--dry-run` to apply. `git apply` works too.
- A green suite says that nothing failed. It does not say that every test
  ran.

## Check

```bash
dsoxlab check vc-boucle-methode
```

Three checks. They rerun pytest on your project themselves, load
`orders.py` to measure its behaviour, and read `SPEC.md` and
`decisions.yaml`.
