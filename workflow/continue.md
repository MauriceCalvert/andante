# Continue

## Current state

Plan 8 (Invention Imitation) active. Phase I4e+I7 issued.

### Active plan
- Plan 8 (Invention Imitation): `workflow/plan_imitation.md`
- Phase I4e+I7 brief: `workflow/task.md`
- I4d (invertible CS) complete. Now re-enabling pre-composed CS in
  the answer phrase and adding episode assignment so the piece breathes.

### Phase sequence
```
I1 (generate/cache FugueTriple) ✓
  → I2 (wire lead_voice through PhrasePlan) ✓
    → I3a (thread fugue param to write_phrase) ✓
      → I3b (subject as notes + monophonic opening) ✓
        → I4a (add imitation_role to PhrasePlan) ✓
          → I4b (answer + countersubject dispatch) ✓
            → I4c (fix tracks, scope, CS) ✓
              → I4d (invertible CS — dual validation) ✓
                → I5 (voice swap + key transposition) ✓
                  → I5b (subject tail generation) ✓
                    → I5c (inject degree for empty tails) ✓
                      → I5c+I6 audit ✓
                        → I4e+I7 (CS playback + episodes) ← CURRENT
```

### Key decisions this session
- I4d confirmed: CP-SAT solver finds solutions 5/5 seeds with dual
  validation. No feasibility issues.
- Combining I4e (CS playback) and I7 (episode assignment) because
  they're one musical outcome: proper exposition + breathing room.
- CS key = tonic (plan.local_key), not dominant. The CS was composed
  at the tonic and validated against both subject and answer degrees.
- Only exordium gets subject + answer + CS. Later sections: one
  subject entry, remaining phrases = episodes (free galant generation).

### Open issues from I5c+I6 audit
1. Soprano writer end-of-phrase repeated pitch (bars 3, 16)
2. ~~Need episode phrases for invention genre~~ → addressed by I7
3. Soprano-bass awareness for cross-relation avoidance

## Key files
- workflow/plan_imitation.md — full imitation plan
- workflow/task.md — current CC task (I4e+I7)
- completed.md — full history (most recent first)
