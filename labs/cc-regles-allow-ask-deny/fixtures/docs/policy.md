# Permission policy of portail-achats

Last week, the coding agent of the team ran `git push -f origin main` and
erased two commits of someone else in the team. The project allows `Bash(git *)`, and the
one deny rule it has, `Bash(git push --force)`, only matches that exact text.

## Project level: `.claude/settings.json` (the team)

The team keeps every allow rule it has today: the agent must still read the
code, run `git status`, `git log`, `git diff` and the tests without asking,
and the team uses `curl` against its own API in tests.

1. **A forced push is always refused**, whatever its form: `--force`, `-f`,
   `--force-with-lease`, and wherever the flag stands in the command
   (`git push --force origin main`, `git push origin main --force`). Write it
   as deny rules: an allow never makes an exception to a deny.
2. **Every other push asks first**, `git push` alone included, even for the
   `feature/*` branches that the team allowed: the rule
   `Bash(git push origin feature/*)` stays in allow, and the agent still asks.

## Managed level: `managed/managed-settings.json` (the security team)

The security team deploys this file on every machine. A project cannot
override it, and the team will not remove its own `Bash(curl *)` allow.

3. **No outbound transfer tool**: `curl` and `wget` are refused.
4. **The `secrets/` folder is never read**, at any depth.

Nothing else is refused at this level: the managed file must not block what
the team needs (reading the code, git, the tests). Do not use
`allowManagedPermissionRulesOnly`: it would drop the team's rules, the
forced-push deny included.
