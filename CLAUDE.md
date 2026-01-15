# Andante Project Guide

You **MUST** read 
`docs/summary.md`
`docs/Tier1_Normative/laws.md`
`docs/test_strategy.md`
`docs/bugs.md`
now.

---

## YAML Conventions

### Token Types

| Type | Rule | Examples |
|------|------|----------|
| Keyword | lowercase, no underscore | `soprano`, `bass`, `hold` |
| Bound constant | uppercase start, must have underscore | `Key_tonic`, `Section_a_bars` |
| Unbound variable | lowercase start, must have underscore | `start_degree`, `phrase_1_bars` |
| Builtin | function name with parentheses | `range()`, `split()` |
| Literal | number, note name, or string | `c`, `major`, `3`, `0.25` |

Every token must be classifiable. Unknown tokens are errors.

### Specific Formats

- Metre: `4/4` not `[4, 4]`
- Ranges: `range(100, 140)` builtin

---

## Communication

- Verdict first, rationale second
- No filler
- Ask if unclear, don't guess
- I use 1-based bar notation

---

## Documentation

Defer updates. Track what needs changing, execute only when explicitly told.

---

## Tests

Do not run the full test suite yourself.
When i ask you to run it, update overage.md and show the final %.

---

## Running Python Scripts

```bash
cd /d/projects/Barok/barok && source .venv/Scripts/activate && cd source/andante && python <script>
```

Key paths:
- **Venv**: `/d/projects/Barok/barok/.venv/Scripts/activate`
- **Working dir**: `/d/projects/Barok/barok/source/andante`

---

## Problem Handling

Quick fixes are forbidden. Changes must be canonical and robust, regardless of effort.

Before changing any code, write out the complete data flow from input to output. 
Identify the single canonical location where the behavior should be controlled. 
Only then propose a change - and get approval before implementing.
