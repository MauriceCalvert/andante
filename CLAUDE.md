# Andante Project Guide — Claude Code

You **MUST** read these files now and keep them in the foreground:
1. `docs/Tier1_Normative/laws.md`
2. `docs/knowledge.md`
3. `workflow/player.md` — your persona and evaluation rules
4. `workflow/chaz.md` — your musical evaluation persona
5. `workflow/bob.md` — your musical ear

## Task System

Check `workflow/task.md` for pending tasks. If it exists, execute it
following the instructions in `workflow/player.md`. When complete
(including the mandatory Chaz checkpoint), write your results to
`workflow/result.md` and delete `workflow/task.md`.

If there is no `workflow/task.md`, ask the user what to do.

---

## Communication

- Verdict first, rationale second
- No filler
- Ask if unclear, don't guess
- Use 1-based bar notation

---

## Documentation

Defer updates. Track what needs changing, execute only when explicitly told.

---

## Testing

Don't test after each change, test once when all changes have been made.
Only test changed code.
Pipeline checkpoint: `python -m scripts.run_tests`. Always. No exceptions.
This runs all 8 genres with fixed seed to `tests/output/`.
The `output/` directory is reserved for the user's brief runs.
NEVER create output2, output3, output_vg3, or any other output variant.
NEVER invent your own test runner. Use `scripts/run_tests.py`.

---

## Coding

Type hint everything.
Try catch blocks are forbidden unless absolutely necessary.
All of Tier1_Normative must always be respected.
Code must be absolutely defensive, always assume that external data (like YAML) is faulty.
Obvious defaults are good. If there's any doubt, throw. For example, assuming 4:4 time is forbidden.
Do not say 'if ...: raise' use asserts.
When you throw, the message must make the fix obvious.
Avoid nested 'if' like the plague, use early returns. If you have to, with & finally.
All constants must reside in shared\constants.
Any function that 'fixes' things is illegal, fix at source.
rng is forbidden in the builder, it must be deterministic.

---

## Problem Handling

Quick fixes are forbidden. Changes must be canonical and robust, regardless of effort.
Don't show changes, make them.

## API Discovery

Never write ad-hoc Python scripts to probe internal APIs. Read the source
files to learn function signatures, return types, and module structure
before writing any code that calls them. Guessing at parameter names or
attribute names wastes time and context window.

## Logging

When code has been added and tested or when a problem has been solved,
append a description of what you did to completed.md.

IMPORTANT: frequent chat crashes. when i ask you to implement something, write a todo and tick off items one by one
so that you can resume in a new chat seamlessly.
