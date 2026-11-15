# portail-achats: invoice module

Purchasing portal of a fictional company, built with Claude Code.

- `facture.py`: invoice lines and totals.
- `tests/`: the test suite, run with `python3 -m unittest -q` from this directory.
- `config/production.toml`: production settings. Changed only through a
  reviewed merge request, never by the agent.
- `config/developpement.toml`: development settings. The agent may change them.
- `outils/verifier_style.py`: the team's style checker, an offline stand-in for
  `ruff check .`. Like ruff, it prints its findings on stdout and exits with 1.
- `.claude/settings.json`, `.claude/hooks/`: the hooks of the project.
- `banc/banc_hooks.py`: the hook bench of the lab (not Claude Code).
