# Trail Windows Local Test

This is the recommended way to test Trail on your real Windows project.

## Status

Trail now has a Windows-native execution fallback.

Important current limitation:

- interactive command output on Windows is sent directly to the console
- transcript capture is currently metadata-only for interactive Windows runs

This is acceptable for a first real test on your local work project.

## Prerequisites

- Windows with Python 3.11+
- `codex` installed and available in `PATH`
- your real project available on the Windows filesystem, not in WSL
- your Codex skill available locally

## Install Trail

Clone the Trail repo on your Windows machine:

```powershell
git clone <your-trail-repo-url>
cd trail
.\scripts\install_windows.ps1
```

After that, use:

```powershell
.\.venv\Scripts\trail.exe --help
```

## First Real Test

In your real work project:

```powershell
cd C:\path\to\your\real\project
<path-to-trail>\.venv\Scripts\trail.exe init
<path-to-trail>\.venv\Scripts\trail.exe project init
```

Register your main skill:

```powershell
<path-to-trail>\.venv\Scripts\trail.exe skill add your-big-skill
<path-to-trail>\.venv\Scripts\trail.exe skill link your-big-skill .
```

Create two real conversations:

```powershell
<path-to-trail>\.venv\Scripts\trail.exe skill run your-big-skill "First real task"
<path-to-trail>\.venv\Scripts\trail.exe convo save

<path-to-trail>\.venv\Scripts\trail.exe skill run your-big-skill "Second real task"
<path-to-trail>\.venv\Scripts\trail.exe convo save
```

Check that the conversations are in the global library:

```powershell
<path-to-trail>\.venv\Scripts\trail.exe convo list --project .
```

Create a specialist agent:

```powershell
<path-to-trail>\.venv\Scripts\trail.exe agent add project-lead --role lead --description "Project lead specialist" --system-prompt "Be precise on status, blockers, delivery risk, and next steps."
```

Link the agent to the project, skill, and conversations:

```powershell
<path-to-trail>\.venv\Scripts\trail.exe agent link project-lead --project . --skill your-big-skill --conversation conv_xxx
<path-to-trail>\.venv\Scripts\trail.exe agent link project-lead --project . --skill your-big-skill --conversation conv_yyy
```

Dry-run the agent first:

```powershell
<path-to-trail>\.venv\Scripts\trail.exe agent run project-lead --dry-run "Prepare a manager-ready status update"
```

## What to validate

- `project init` creates a correct global project record
- `skill add` and `skill link` work with your real skill
- two conversation records exist in `trail convo list --project .`
- `agent run --dry-run` produces a clearly better prompt than your raw skill
- `trail run -- codex mcp list` shows `trail` as an attached MCP server

## Recommended moment to test

Test on your real Windows project when all of this is true:

- the repo is cloned locally
- `install_windows.ps1` completes successfully
- `trail.exe --help` works
- `trail project init` works in a scratch repo or test repo

At that point, move to your real work project and do the 2-conversation test.
