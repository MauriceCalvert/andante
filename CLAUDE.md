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

Do not run test suites (`pytest`, `run_tests`, or any test runner).
The user runs test suites separately and will report any failures.
NEVER invent your own test runner.

## Pipeline and Evaluation

After completing all code changes, you MUST:

1. **Run the pipeline yourself.** This is not a test suite — it is the
   composition pipeline and you must run it to evaluate your work.
   ```
   python -m scripts.run_pipeline briefs\builder\invention.brief -v -trace -seed 42 -o output
   ```
   Output goes to `andante/output/` with bare genre name (e.g.
   `invention.mid`, not `invention_c_major.mid`). NEVER create output2,
   output3, or any variant directory.

2. **Run the Bob → Chaz checkpoint** from the task brief. Read the .note
   and .trace files. Write Bob's assessment first (perceptual only), then
   Chaz's diagnosis (architectural only). Answer every question in the
   task brief's Checkpoint section.

3. **Write `result.md`** with: code changes, Bob's assessment, Chaz's
   diagnosis, and end with: "Please listen to the MIDI and let me know
   what you hear."

4. **Delete `task.md`**.

5. **Document what you did at the top of completed.md with date and timestamp**.

6. **If the task completed successfully, commit and push**.

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

