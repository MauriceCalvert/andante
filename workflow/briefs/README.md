# Viterbi Integration Briefs

Execute in order. Each brief is self-contained for Claude Code.
Copy to `workflow/task.md` one at a time; wait for `result.md` before proceeding.

| #  | File                     | Scope                                      | Depends on |
|----|--------------------------|---------------------------------------------|------------|
| 1  | v0a-rename-cleanup.md    | Rename splines→viterbi, strip prints        | —          |
| 2  | v0b-test-16-beats.md     | Add 16-beat demo example                    | V0a        |
| 3  | v1-key-aware.md          | KeyInfo, key-aware pitch sets & distances   | V0a        |
| 4  | v2-subbeat-timing.md     | Float beats, beat strength classification   | V1         |
| 5  | v3-enhanced-costs.md     | Cross-relation, spacing, interval quality   | V2         |
| 6  | v4-wire-soprano.md       | Adapter module, replace soprano span pipeline | V3       |
| 7  | v5-wire-invention.md     | Bidirectional leader/follower for inventions | V4        |
| 8  | v6-retire-spans.md       | Delete dead span code                       | V5         |
| 9  | v7-bach-compare.md       | Bach sample comparison script + analysis    | V3         |

Note: V7 depends on V3 (key awareness + sub-beat + enhanced costs) but
NOT on V4-V6 (real system integration). V7 can run in parallel with V4-V6
or immediately after V3.

## Execution sequence

Minimal path to Bach comparison: V0a → V1 → V2 → V3 → V0b → V7

Full integration path: V0a → V0b → V1 → V2 → V3 → V4 → V5 → V6 → V7
