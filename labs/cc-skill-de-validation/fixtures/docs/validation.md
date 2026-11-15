# Validation of portail-achats

Before a pull request, the project goes through three checks, in this
order. The scripts are in `tools/validation/`; the CI runs them directly,
as programs, from the project root.

| Order | Script | Arguments | What it checks |
|---|---|---|---|
| 1 | `check_style.py` | `src tests` | line length, tabs, trailing spaces |
| 2 | `run_tests.py` | none | the unit tests of `tests/` |
| 3 | `check_secrets.py` | `src` | access keys and passwords written in the code |

Every check runs, even when an earlier one fails: the report must list
every failure, not only the first one.

## The /valider skill

A first version of the skill was started in `.claude/skills/valider/`. It
was never loaded by Claude Code, and nobody has run it to the end.

What the team decided:

- the skill is **self-contained**: its scripts live in its own `scripts/`
  folder, so that copying `.claude/skills/valider/` into another repository
  brings the whole procedure with it. The scripts are copied unchanged;
- the scripts are called **directly**, as programs, like the CI does: they
  must be executable;
- `allowed-tools` pre-approves exactly the three calls, and nothing else:
  no bare `Bash`, no pattern that would let another command through;
- the validation is started **on demand only**, with `/valider`: Claude
  must not start it on its own.
