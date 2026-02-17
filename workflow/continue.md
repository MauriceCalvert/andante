# Continue

## Current state

All invention improvement phases complete: CP1–4, F1–3, Groups A–E,
I5+I8. Invention is parked — further refinement deferred.

Galant genres closed.

## Direction

Three-voice fugue chosen as next genre. Before building the fugue
pipeline, the subject generator needs a redesign:

- Current generator is random-search with post-hoc filtering
- Needs archetype-based generation driven by affect, genre, mode, metre
- Subject character should flow from the rhetorical framework (L1)
- Must produce subjects that fragment well for episodes

Design discussion in progress. Next step: catalogue WTC I subject
types, distil into archetype vocabulary, design generation chain:

```
affect + genre + mode + metre
    → archetype selection
    → contour instantiation
    → rhythm binding
    → answer analysis
    → fragment analysis
```

## Key files

- `workflow/fugue_scoping.md` — three-voice fugue architecture analysis
- `workflow/improve.md` — invention improvement plan (complete)
- `workflow/todo.md` — full backlog
- `motifs/subject_generator.py` — current subject generator (to redesign)
- `motifs/head_generator.py` — current head generator
- `motifs/tail_generator.py` — current tail generator
