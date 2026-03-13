# Windows Checklist

Use this on your local Windows PC before testing Trail on your real work project.

## 1. Clone and install

```powershell
git clone https://github.com/iluxu/trail.git
cd trail
.\scripts\install_windows.ps1
```

Expected:

- the script completes without error
- `.\.venv\Scripts\trail.exe --help` works

## 2. Smoke test in a small repo

In any small test repo on Windows:

```powershell
<path-to-trail>\.venv\Scripts\trail.exe init
<path-to-trail>\.venv\Scripts\trail.exe project init
<path-to-trail>\.venv\Scripts\trail.exe status --brief
```

Expected:

- `.trail\` is created in the repo
- `trail project init` returns a project record
- `trail status --brief` returns a valid summary

## 3. Register your real skill

```powershell
<path-to-trail>\.venv\Scripts\trail.exe skill add your-big-skill
<path-to-trail>\.venv\Scripts\trail.exe skill link your-big-skill .
<path-to-trail>\.venv\Scripts\trail.exe skill show your-big-skill
```

Expected:

- the skill is stored in `~/.trail/skills/`
- the skill is linked to the current project

## 4. Create two real conversations

```powershell
<path-to-trail>\.venv\Scripts\trail.exe skill run your-big-skill "First real task"
<path-to-trail>\.venv\Scripts\trail.exe convo save

<path-to-trail>\.venv\Scripts\trail.exe skill run your-big-skill "Second real task"
<path-to-trail>\.venv\Scripts\trail.exe convo save
```

Expected:

- `trail convo list --project .` shows two conversations

## 5. Create one specialist agent

```powershell
<path-to-trail>\.venv\Scripts\trail.exe agent add project-lead --role lead --description "Project lead specialist"
<path-to-trail>\.venv\Scripts\trail.exe agent link project-lead --project . --skill your-big-skill --conversation conv_xxx
<path-to-trail>\.venv\Scripts\trail.exe agent link project-lead --project . --skill your-big-skill --conversation conv_yyy
<path-to-trail>\.venv\Scripts\trail.exe agent run project-lead --dry-run "Prepare a manager-ready status update"
```

Expected:

- the agent is linked to the project, skill, and both conversations
- the `dry-run` prompt is clearly better than the raw skill alone

## 6. MCP check

```powershell
<path-to-trail>\.venv\Scripts\trail.exe run -- codex mcp list
```

Expected:

- `trail` appears as an attached MCP server for the session

## Send back

If you want help after the first local run, send back:

- output of `trail project show`
- output of `trail skill show your-big-skill`
- output of `trail convo list --project .`
- output of `trail agent show project-lead`
- whether `trail run -- codex mcp list` showed `trail`
