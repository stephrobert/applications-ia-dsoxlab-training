# Incident: the reviewer fixed the code itself

During the review of branch `feat/discount-codes`, the team asked the
`relecteur` subagent for a report. It read the diff, then went further:

1. it ran `ruff check --fix src`, which rewrote two files;
2. it edited `src/orders.py` to "fix" a rounding it found suspicious;
3. it wrote its report into `docs/review.md`, a file of the repository;
4. it committed everything and pushed the branch;
5. it closed the tracker issue PA-112.

Its instructions say "You never modify a file". They were in the prompt, and
the prompt is not a barrier: the subagent had every tool of the session,
because its file has no `tools` field.

The full list of calls it attempted is in `bench/review.json`.

Decision of the team: the reviewer keeps what a review needs (read the code,
search it, read the git history and the diff, read the tracker issue) and
loses everything that writes. The `correcteur` subagent is not concerned: it
is the one that applies fixes, on request, and its tools stay as they are.
