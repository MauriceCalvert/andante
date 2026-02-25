# Workflow: Two-Claude Architecture

## Overview

Andante uses two Claude instances in a conductor/player arrangement:

- **Conductor** (Claude Desktop or claude.ai): Sets direction, writes
  task briefs, evaluates musical results. Never writes code.
- **Player** (Claude Code CLI): Implements code changes, runs the
  pipeline, evaluates output as Bob then Chaz. Never sets direction.

They communicate through files in this folder. The user types "go" in
Claude Code and relays results back to the conductor.

## Files

| File | Purpose | Written by | Read by |
|------|---------|-----------|---------|
| `conductor.md` | Conductor role, task template, evaluation protocol | — | Conductor |
| `player.md` | Player role, Chaz rules, iron law, checkpoint protocol | — | Player |
| `chaz.md` | Architectural diagnosis persona | — | Player |
| `bob.md` | Musical ear persona | — | Player |
| `todo.md` | Current and parked tasks | Conductor | Both |
| `tb-plan.md` | Thematic Bias phase plan (current work) | Conductor | Conductor |
| `task.md` | Current task brief (transient) | Conductor | Player |
| `result.md` | Task results (transient) | Player | Conductor |

`task.md` and `result.md` are transient. `task.md` is deleted by the
player after execution. `result.md` is overwritten each cycle.

Design documents live in `docs/`, not here. Completed task briefs are
logged in `completed.md` and deleted from this folder.

## The Loop

```
1. Conductor writes workflow/task.md
2. User types "go" in Claude Code
3. Player reads CLAUDE.md → laws.md, knowledge.md, player.md,
   chaz.md, bob.md → task.md
4. Player implements, runs pipeline, evaluates as Bob then Chaz,
   writes result.md, deletes task.md
5. User tells Conductor "read the result"
6. Conductor reads result.md → approves or rejects
```

## Running the Pipeline

```
cd D:\projects\Barok\barok\source\andante
python -m scripts.run_pipeline briefs\builder\invention.brief -v -trace -seed 42 -o output
```
