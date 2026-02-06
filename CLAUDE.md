# Andante Project Guide

You **MUST** read 
`docs/Tier1_Normative/laws.md` and `docs/knowledge.md`
now and keep them in the foreground for the whole chat.

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
Full test suite takes a long time, ask before running.

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

## Logging

When code has been added and tested or when a problem has been solved,
append a description of what you did to completed.md.

IMPORTANT: frequent chat crashes. when i ask you to implement something, write a todo and tick off items one by one
so that you can resume in a new chat seamlessly.
