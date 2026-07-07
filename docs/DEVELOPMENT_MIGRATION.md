# Hermes Development Machine Migration

This guide is for moving Hermes development to another Windows computer.
It is different from customer installation: source code comes from Git, while
the private Python runtime, venv dependencies, and offline Node.js are prepared
by the installer/bootstrap package.

## Recommended clone location

Use `%LOCALAPPDATA%` instead of a hard-coded user name:

```bat
cd /d %LOCALAPPDATA%
git clone https://gitee.com/yao-deting/hermes.git hermes
git clone https://gitee.com/yao-deting/hermes-console.git hermes-console
```

For user `yao`, this expands to:

```text
C:\Users\yao\AppData\Local\hermes
C:\Users\yao\AppData\Local\hermes-console
```

## Runtime layout

The source repository does not track these runtime folders:

```text
runtime\python311
hermes-agent\venv
offline\node
offline\wheels
state.db
logs
sessions
cache
memories
```

Prepare them with `hermes-install` or a local bootstrap script after cloning.
This keeps the source repository small and avoids carrying personal runtime
state to another machine.

## Path rules

Avoid committing paths such as:

```text
C:\Users\dtyao\...
D:\hermes_workspace\...
D:\AI\project\hermes-install
```

Prefer:

```text
%LOCALAPPDATA%\hermes
Path.home()
Configured workspace directory
Employee work_dir configured in the desktop UI
```

If an employee has a machine-specific `work_dir`, update it after cloning on the
new computer.

## Before pushing

Check that the commit only includes source/configuration files that should move
to another development machine. Do not commit:

```text
state.db*
auth.json
.env
logs
sessions
execution_evidence
desktop-client/state.json
desktop-client/static/_bubble*.bmp
skills/.usage.json
skills/.curator_state
```
