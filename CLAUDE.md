# Andante Project Guide

You **MUST** read 
`docs/summary.md`
`docs/Tier1_Normative/laws.md`
`docs/Tier2_Architecture/*.md`
`docs/Tier3_Guides/bob.md`
now and keep them in the foreground for the whole chat.

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
- Offsets and durations are in *whole notes*, not quarter notes.

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
manifest constants must be in shared\constants.py

---

## Tests

Do not write or run tests yourself.
When i ask you to run them, add missing tests, fix as needed. 
when done, update coverage.md and show the final %.


---

## Running Python Scripts

```bash
cd /d/projects/Barok/barok && source .venv/Scripts/activate && cd source/andante && PYTHONPATH=. python <script>
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

---

## Git Workflow

Auto-commit after each bug fix that passes tests or after adding functionality. No prompt needed.

---

## PowerShell Execution (Windows MCP)

Direct calls to external processes (python.exe, pytest.exe) hang indefinitely.
Use `Start-Process` with `-WindowStyle Hidden -Wait` to run commands silently.

### Running Python scripts or pytest

```powershell
# Step 1: Run command hidden, redirect to file
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c "cd /d D:\projects\Barok\barok\source\andante && D:\projects\Barok\barok\.venv\Scripts\python.exe -m pytest tests/ -v > D:\temp_output.txt 2>&1"' -WindowStyle Hidden -Wait

# Step 2: Read the output
Get-Content D:\temp_output.txt
```

### Running a Python script file

```powershell
# Step 1
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c "cd /d D:\projects\Barok\barok\source\andante && D:\projects\Barok\barok\.venv\Scripts\python.exe my_script.py > D:\temp_output.txt 2>&1"' -WindowStyle Hidden -Wait

# Step 2
Get-Content D:\temp_output.txt
```

### Git commands

Git is NOT in PATH in the MCP context. Always use the full path.

**Git path**: `C:\Program Files\Git\cmd\git.exe`

```powershell
# Step 1: Run git command
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c ""C:\Program Files\Git\cmd\git.exe" status > D:\temp_output.txt 2>&1"' -WindowStyle Hidden -Wait

# Step 2: Read output
Get-Content D:\temp_output.txt
```

Use git's `-C` flag for working directory (avoids escaping issues with `cd &&`):
```powershell
# Step 1: git add and commit (repo root is source/andante)
Start-Process -FilePath "C:\WINDOWS\system32\cmd.exe" -ArgumentList '/c ""C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante add -A && "C:\Program Files\Git\cmd\git.exe" -C D:\projects\Barok\barok\source\andante commit -m "Fix: description" > D:\temp_output.txt 2>&1"' -WindowStyle Hidden -Wait

# Step 2
Get-Content D:\temp_output.txt
```

### Key points

- **Always use two separate tool calls**: one to run, one to read output
- **Always use `-WindowStyle Hidden`**: prevents flashing windows
- **Always use `-Wait`**: ensures command completes before reading output
- **Use single quotes** around `-ArgumentList` value, double quotes inside
- **Temp file**: use `D:\temp_output.txt` or similar
- Simple PowerShell commands (Get-Content, Test-Path, Remove-Item, Set-Location) work directly without Start-Process
