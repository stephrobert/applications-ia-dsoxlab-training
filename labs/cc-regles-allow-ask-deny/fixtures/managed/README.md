# managed/

This folder stands for the managed settings of the machine. On a real Linux
or WSL machine, the file is `/etc/claude-code/managed-settings.json`, deployed
by the fleet management tool; on macOS,
`/Library/Application Support/ClaudeCode/managed-settings.json`. The agent of
this lab reads `managed/managed-settings.json` instead, so that you do not
need root access.

Its format is the format of any settings file:
`{"permissions": {"deny": [...], "ask": [...], "allow": [...]}}`.
