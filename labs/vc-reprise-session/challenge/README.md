# Challenge: Take over a slice that a session left half done

## Situation

Yesterday, a coding agent worked on the **portail-achats**, the purchasing
portal of a fictional company. Its task: the order lifecycle described in
`SPEC.md`, one slice at a time. It finished slices S1 and S2, started S3
(criteria AC-4 and AC-5), and the session stopped: the context was full.

Today a new session starts, yours. It remembers nothing of yesterday. What
is left is the repository: the commits, the files nobody committed, and
`PROGRESS.md`, the journal the previous session kept for the next one. That
journal was written by the session that stopped. Check it against Git
before you believe it.

Everything is in `challenge/work`:

| Path | Content |
|---|---|
| `portail-achats/` | the project, a Git repository: work from here |
| `portail-achats/SPEC.md` | the requirements R1 to R4, the criteria AC-1 to AC-7 and the slices |
| `portail-achats/PROGRESS.md` | the journal of the previous session |
| `portail-achats/orders.py` | the module, implemented criterion by criterion |
| `portail-achats/tests/` | one test file per slice |
| `.git-portail-achats/` | the Git database of the project. `portail-achats/.git` is a file that points to it. Leave it alone and use `git` from `portail-achats/` |

## Mission

1. **Rebuild the real state.** `git log --oneline`, `git status`, then
   `git diff` file by file, then `pytest -v`. Write down what is committed,
   what is not, and what passes. Compare it with `PROGRESS.md`.
2. **Sort the uncommitted work**, file by file: keep it (it ends up in a
   commit) or discard it (`git restore <file>` for a modified file). A
   kept file can be corrected before you commit it.
3. **Never change `SPEC.md` or the tests of the criteria already done**
   (AC-1 to AC-3). If such a test fails, the code is wrong, not the test.
4. **Finish slice S3**: AC-4 and AC-5 as `SPEC.md` words them, each one with
   the test that `SPEC.md` cites, under that exact name. The whole suite
   must pass.
5. **Commit on top of the existing history.** Add new commits; do not
   amend, reset or rebase the commits that are already there.
6. **Update `PROGRESS.md`** for the next session, then commit it:
   - each criterion of the table gets its true state (`done`, `in progress`,
     `to do`) and, when it is done, the short hash of the first commit in
     which it passes;
   - the line `Next action:` names a criterion that is not done yet;
   - in the session log, one line per uncommitted file you found at the
     start, with your decision and why:
     `- orders.py: kept ...` or `- tests/test_x.py: discarded ...`.

   At the end, `git status` prints nothing.

## Pointers

- Git needs an identity to commit. If `git commit` asks for one:
  `git config user.name "Your name"` and `git config user.email "you@example.org"`,
  from `portail-achats/`.
- `git diff <file>` shows what changed in one file; `git status` lists the
  new files that Git does not track yet.
- A commit cannot contain its own hash. Commit the code first, then
  `PROGRESS.md` in a second commit that cites the first.
- The table and the lines of `PROGRESS.md` can be written in French:
  `fait`, `en cours`, `à faire`, `Prochaine action :`, `gardé`, `écarté`.

## Check

```bash
dsoxlab check vc-reprise-session
```

Four checks. They take the truth from the starting repository, which they
rebuild from the lab's fixtures, never from your files. They run your tests
and reference tests on a copy of your last commit, then on versions of
`orders.py` that break one criterion each: the test `SPEC.md` cites for
that criterion must fail. They read the history and `git status`, compare
the SHA-256 fingerprints of `SPEC.md` and of the done tests with the
starting ones, and check every line of `PROGRESS.md` against the commits.
