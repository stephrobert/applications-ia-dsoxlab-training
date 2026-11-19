# Challenge: A hook that succeeds, blocks and crashes

## Read this first: what is simulated

This lab runs **without Claude Code** and calls no AI service. It ships a
**hook bench**, `banc/banc_hooks.py`, a Python script that does for hooks
what Claude Code does:

| | Real or simulated |
|---|---|
| Your hooks (the commands in `.claude/settings.json`) | **real**: the bench runs them, with the event as JSON on stdin and `CLAUDE_PROJECT_DIR` set |
| The events (a Bash command, an edit, the end of a turn) | **simulated**: fixed JSON files in `banc/evenements/`. Nothing is deleted or edited |
| What Claude Code does with the exit code and the output of a hook | **simulated**, from the official documentation: blocked or not, what Claude reads, what you see |
| The model | **absent**: no answer, no reaction |

Each event runs in a throwaway copy of the project: a hook may read and run
whatever it needs, your files are never touched. The bench writes what
happened in `banc/journal.json`. Its header lists every rule it applies, and
what it does not simulate (permission rules, `onFailure`, `async`...). A
full score proves that your hooks give the right exit code and the right
output. It does not prove that Claude, the model, will then act well.

## Situation

The **portail-achats** team has three hooks in `.claude/settings.json`. On
paper they protect the project. In practice:

| Event | Hook | What it should do |
|---|---|---|
| `PreToolUse` on `Bash` | `.claude/hooks/garde_tests.py` | block any command that deletes the test suite |
| `PostToolUse` on `Edit\|Write` | `python3 outils/verifier_style.py` | tell Claude about the style errors it just wrote |
| `Stop` | `python3 -m unittest -q` | send Claude back to work when it ends its turn with a failing test |

A fourth rule exists only in the README: the agent must never change
`config/production.toml`. No hook enforces it.

## What the exit codes mean

This is the whole lab. A hook speaks to Claude Code only through its exit
code and its output:

| Exit code | PreToolUse | PostToolUse | Stop |
|---|---|---|---|
| **0** | the call goes on; a JSON decision on stdout can still refuse it | nothing reaches Claude | Claude stops |
| **2** | the call is **blocked**; Claude reads **stderr** | the tool already ran; Claude reads **stderr** | Claude **does not stop**; it reads **stderr** and goes on |
| **any other** (1 included) | non-blocking error: the call **goes on** | non-blocking error: Claude reads nothing | non-blocking error: Claude stops |

On a non-blocking error, you see a notice in the session. Claude does not.
Exit code 1 is the usual failure code in Unix, so it is also what a crashing
Python script returns: a guard that crashes lets everything through.

On these three events, Claude never reads stdout. Only stderr, and only with
exit code 2.

## Mission

Work in `challenge/work`.

1. **Replay the hooks as they are**: `python3 banc/banc_hooks.py`. Nine
   events are played. Read each line: the outcome, the exit code of each
   hook, what you would see, what Claude would see. Open
   `banc/journal.json` for the full stdout and stderr.
2. **Repair the guard** `garde_tests.py`. Run it alone first, on the JSON it
   receives:
   `python3 banc/banc_hooks.py --print-input 02 | python3 .claude/hooks/garde_tests.py; echo "exit $?"`.
   It must block the deletion of the tests (`rm -rf tests/`, but also
   `git rm -r tests` or `rm -f ./tests/test_facture.py`) with **exit code 2**
   and a reason on **stderr**, and let every other command go on with exit
   code 0, without crashing.
3. **Make the style checker heard.** The checker behaves like ruff: findings
   on stdout, exit code 1. Change the `PostToolUse` command so that its
   findings reach Claude, and so that a clean file gives exit code 0.
4. **Make the Stop hook stop the turn when a test fails**, with the test
   report sent to Claude, and let Claude stop when the tests pass.
5. **Protect `config/production.toml`** with a new `PreToolUse` hook on
   `Edit|Write`. This one must not use exit code 2: it **exits 0** and prints
   a JSON decision on stdout (format below). Every other file stays
   editable, `config/developpement.toml` included.
6. **Replay the bench** after your last change. Its journal must say what
   your final hooks do.

## The JSON decision of a PreToolUse hook

With exit code 0, a PreToolUse hook can print **one JSON object, and
nothing else**, on stdout:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Why the call is refused. Claude reads this."
  }
}
```

- `permissionDecision`: `deny` refuses the call, `ask` asks you, `allow`
  skips the permission prompt.
- The decision lives **inside** `hookSpecificOutput`, which must name its
  event in `hookEventName`. A `permissionDecision` at the top level is not
  read.
- The JSON is read only with exit code 0. With exit code 1, it is ignored.
  With exit code 2, the call is blocked anyway.
- For an `Edit` or a `Write`, the path is in `tool_input.file_path`, as an
  **absolute** path.

## Pointers

- The shape of a hook entry in `.claude/settings.json`:

  ```json
  {"matcher": "Edit|Write",
   "hooks": [{"type": "command",
              "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/your-hook.py\"",
              "timeout": 10}]}
  ```

  Several entries can sit under the same event. `Stop` takes no matcher.
- **Matcher**: `"*"`, `""` or no matcher means every tool. A value made only
  of letters, digits, `_`, `-`, spaces, commas and `|` is an exact name or a
  list (`Edit|Write`). Any other character makes it a regular expression
  that may match part of a name: `Edit.*` also matches `NotebookEdit`.
- **The JSON a hook receives** always carries `session_id`, `cwd`,
  `hook_event_name` and a few more fields. For `PreToolUse`, it adds
  `tool_name`, `tool_input` and `tool_use_id`. For a Bash call, the command
  is in `tool_input.command`. `--print-input` shows the exact JSON.
- **A shell command can choose its streams and its exit code.** `1>&2` sends
  stdout to stderr. `cmd || exit 2` exits with 2 when `cmd` fails, and with
  0 when it succeeds.
- `python3 banc/banc_hooks.py --only 07` replays only the events whose name
  starts with `07`.
- The hook runs with `python3`: use the standard library only.

## Check

```bash
dsoxlab check cc-hook-qui-echoue
```

Five checks. Each one replays the bench of the lab on your hooks: editing
`banc/banc_hooks.py` or the events changes nothing. They also add events of
their own: other ways of deleting the tests, another style error, another
failing test, a `Write` on the production settings. And they compare your
`banc/journal.json` with what your hooks do now.
