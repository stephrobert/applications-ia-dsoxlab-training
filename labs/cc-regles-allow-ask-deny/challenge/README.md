# Challenge: A forced push that the rules let through

## Read this first: what is simulated

The agent of this lab is **a Python script, not Claude Code**. It calls no AI
service, needs no network, and never runs the actions of its scenario. It
reads the permission rules of two settings levels and says what they decide
for each action:

| Level | File in this lab | Real file |
|---|---|---|
| managed | `managed/managed-settings.json` | `/etc/claude-code/managed-settings.json` on Linux and WSL, deployed by the organisation |
| project | `.claude/settings.json` | the same, shared by the team through git |

What it applies: the rules of both levels **merge**, they do not replace
each other. Every `deny` is read first, then every `ask`, then every
`allow`, and the first rule that matches decides. A more precise rule does
not change that order. `allowManagedPermissionRulesOnly: true` in the
managed file drops the project rules. The rule syntax (`Bash(...)`,
`Read(...)`) is listed in the header of `agent/agent.py`.

What it does not apply: user settings, `settings.local.json`, permission
modes, hooks, the sandbox, and the split of a command into its parts that a
real agent makes. So a full score proves that your rules **say** the right
thing to this agent. It does not prove what a given version of Claude Code
does in a session: that is the part of this lab that runs in a real session,
published separately.

## Situation

Last week, the coding agent of **portail-achats** ran a forced push to
`main` and erased two commits of someone else in the team. The project allows
`Bash(git *)`, and its one deny rule matches one exact text only.

The team and the security team wrote a policy in `docs/policy.md`.
Everything is in `challenge/work`:

| File | Content |
|---|---|
| `.claude/settings.json` | the rules of the team, as they are today |
| `managed/` | stands for the managed settings of the machine (empty for now) |
| `docs/policy.md` | the policy, project level and managed level |
| `agent/agent.py`, `agent/scenario.json` | the simulated agent and the actions of the incident |
| `src/`, `secrets/` | the code, and credentials the agent must never read |

## Mission

1. **Run the agent as it is**, from `challenge/work`:
   `python3 agent/agent.py`. Every action of the incident is allowed.
2. **Project level**: in `.claude/settings.json`, refuse every form of
   forced push with deny rules, and make every other push ask first with an
   ask rule. **Keep every allow rule of the team**, `Bash(git *)` and
   `Bash(git push origin feature/*)` included.
3. **Managed level**: create `managed/managed-settings.json` and refuse
   `curl`, `wget` and the reading of `secrets/`, at any depth. Nothing else:
   the team must still read the code, use git and run the tests.
4. **Run the agent again** after your last change. Its journal,
   `agent/journal.json`, must say what it decides on your final files.

## Pointers

- A rule matches the **text** of the command. `Bash(git push --force *)`
  accepts `git push --force` and `git push --force origin main`, but not
  `git push origin main --force`. Count the places where a flag can stand.
- A pattern ending with ` *` also accepts the bare command:
  `Bash(git push *)` covers `git push` alone.
- `*` stands for any text, letters included: a pattern that looks for `-f`
  anywhere in the command also catches a branch named `price-format`.
- An allow never makes an exception to a deny, and an ask still asks when a
  more precise allow matches. That is why the team can keep its allow rules.
- `Read(./secrets/*)` stays inside one directory; `**` crosses directories.
- A deny in the project protects this project only, and a contributor can
  change it. A deny in the managed file applies to every project of the
  machine, and no project can override it.

## Check

```bash
dsoxlab check cc-regles-allow-ask-deny
```

Four checks. Each one runs the agent of the lab again, on a copy of your
project, with **actions that `agent/scenario.json` does not show**: other
forms of forced push, other pushes, other reads of `secrets/`. One check
first **adds to the project** an allow rule for `wget` and for `secrets/`,
and expects the managed level to refuse them anyway. Editing
`agent/agent.py` changes nothing.
