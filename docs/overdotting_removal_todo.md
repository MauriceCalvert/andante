# Overdotting Removal TODO — ALL COMPLETE

Law S001 added. All overdotting removed.

## Constants (`shared/constants.py`)
- [x] 1. Remove `OVERDOTTED_CHARACTERS`
- [x] 2. Remove `OVERDOTTING_FACTORS`
- [x] 3. Remove `VALID_OVERDOTTING_LEVELS`

## Voice planning (`planner/voice_planning.py`)
- [x] 4. Remove `OVERDOTTED_CHARACTERS` import
- [x] 5. Remove `overdotted=` from both GapPlan constructors

## Figuration loader (`builder/figuration/loader.py`)
- [x] 6. Remove overdotted from template key; key becomes `(note_count, metre)`
- [x] 7. Skip `overdotted` variant entries when loading

## Figuration types (`builder/figuration/types.py`)
- [x] 8. Remove `overdotted` field from `RhythmTemplate`

## Figuration strategy (`builder/figuration_strategy.py`)
- [x] 9. Remove `gap.overdotted` from template lookup key
- [x] 10. Remove overdotted fallback logic

## Cadential strategy (`builder/cadential_strategy.py`)
- [x] 11. Remove `gap.overdotted` from template lookup key
- [x] 12. Remove overdotted fallback logic

## Rhythm templates YAML (`data/figuration/rhythm_templates.yaml`)
- [x] 13. Remove all `overdotted:` variant blocks

## Affect profiles YAML (`data/rhythm/affect_profiles.yaml`)
- [x] 14. Remove `overdotting:` field from all entries

## Rhythmic gap planner (`planner/rhythmic_gap.py`)
- [x] 15. Remove `OVERDOTTING_FACTORS` import
- [x] 16. Remove `apply_overdotting` function
- [x] 17. Remove overdotting call in gap rhythm builder

## Rhythmic profile loader (`planner/rhythmic_profile.py`)
- [x] 18. Remove `VALID_OVERDOTTING_LEVELS` import
- [x] 19. Remove overdotting validation and loading

## Builder types (`builder/types.py`)
- [x] 20. Remove `overdotting` field from `RhythmicProfile`

## Test files (`revision/test_*.py`)
- [x] 21. Remove `overdotted=False` from GapPlan constructors in tests

## Completed
- [x] 22. Log to completed.md
