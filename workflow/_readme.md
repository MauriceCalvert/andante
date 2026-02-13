# Workflow: Two-Claude Architecture

## Overview

Andante uses two Claude instances in a conductor/player arrangement:

- **Conductor** (Claude Desktop or claude.ai web chat): Sets direction,
  writes task briefs, evaluates musical results. Never writes code.
- **Player** (Claude Code CLI): Implements code changes, runs the pipeline,
  evaluates output using the Chaz persona. Never sets direction.

They communicate through files in this folder. The user's only job is
typing "go" in Claude Code and relaying results back to the conductor.

## Why Two Claudes

Claude has a documented failure mode: when reading Python, it evaluates
against programming criteria and musical criteria silently disappear.
The Chaz persona (chaz.md) prevents this by enforcing musical judgment
before code analysis. But persona instructions compete with implementation
focus in a single context.

Separating the roles means:
- The conductor never sees Python, so musical judgment stays clean.
- The player has Chaz baked into its startup (via CLAUDE.md → player.md),
  so the musical frame is established before any code is read.
- Neither instance needs to self-identify; they have different entry
  points by construction.

## Entry Points

| Instance | Entry point | How |
|----------|------------|-----|
| Conductor | `workflow/conductor.md` | Memory edit reads it at every chat start |
| Player | `CLAUDE.md` (project root) | Claude Code auto-reads it at session start |

Both read the shared project knowledge (laws.md, knowledge.md) from
their respective entry points. They never read each other's role file.

Memory edits are private to the conductor. Claude Code has no memory system.

## Files in This Folder

| File | Purpose | Written by | Read by |
|------|---------|-----------|---------|
| `conductor.md` | Conductor's role, task template, evaluation protocol | — | Conductor |
| `player.md` | Player's role, Chaz rules, iron law, checkpoint protocol | — | Player |
| `chaz.md` | Musical evaluation persona (ears before eyes) | — | Player |
| `bob.md` | Musical ear persona (perceptual vocabulary) | — | Player |
| `task.md` | Current task brief | Conductor | Player |
| `result.md` | Task results including Chaz checkpoint | Player | Conductor |
| `readme.md` | This file | — | Humans |

`task.md` and `result.md` are transient. `task.md` is deleted by the
player after execution. `result.md` is overwritten each cycle.

## The Loop

```
1. Conductor writes workflow/task.md
       ↓
2. User types "go" in a fresh Claude Code session
       ↓
3. Claude Code reads CLAUDE.md
       → reads laws.md, knowledge.md
       → reads player.md, chaz.md, bob.md  (becomes Chaz)
       → reads task.md                     (gets the brief)
       ↓
4. Claude Code implements the task
       → makes code changes
       → runs the pipeline
       → evaluates output AS CHAZ (mandatory checkpoint)
       → writes workflow/result.md
       → deletes workflow/task.md
       ↓
5. User tells Conductor "read the result"
       ↓
6. Conductor reads workflow/result.md
       → judges Chaz checkpoint quality (genuine or performed?)
       → reads output files if needed (as Bob)
       → approves → logs to completed.md, writes next task.md
       → or rejects → writes corrected task.md with explanation
       ↓
   Back to step 2.
```

## Task Brief Format

Task briefs follow the template in conductor.md:

```
## Task: [Phase ID] — [Name]

### Musical Goal
[What should change in what you hear]

### Implementation
[Specific code changes, files to modify]

### Constraints
[What not to do]

### Checkpoint (mandatory)
After implementation, run the pipeline. Then answer as Chaz:
1. What changed musically? (cite specific bars)
2. What's still wrong?
3. Is the genre recognisable yet?

### Acceptance Criteria
[Musical criteria, not technical ones]
```

## Failure Modes and Remedies

**Player skips Chaz checkpoint or gives perfunctory answer:**
Conductor rejects the result. Write a corrected task.md that repeats the
checkpoint requirement. If persistent, revise player.md to strengthen
the language.

**Player proposes new code instead of wiring dead systems:**
Conductor rejects. Corrected task.md should name the specific existing
module to wire.

**Player evaluates technically instead of musically:**
("The trace shows 9 schemas" instead of "every other phrase is a full stop")
Start a fresh Claude Code session. The Chaz frame re-establishes on
CLAUDE.md re-read. If persistent, revise player.md.

**Conductor loses musical frame and starts thinking about code:**
Re-read conductor.md. You do not write code. You judge music.

**Chat crash mid-task:**
Player uses a todo list (per CLAUDE.md instructions) and can resume in a
new session. The task.md still exists (only deleted on completion).

## Running the Pipeline

From the project root:
```
cd D:\projects\Barok\barok\source\andante
python -m scripts.run_pipeline minuet default g_major -o output -trace
python -m scripts.run_pipeline gavotte default d_major -o output -trace -seed 42
```

Output goes to `output/`. The player reads the .note and .trace files
for Chaz evaluation.

## Current State

Viterbi solver (V0–V9) and bass Viterbi (BV1) complete.
See `completed.md` for full history, `continue.md` for next steps,
`todo.md` for deferred work.
