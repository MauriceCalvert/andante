# Inequality Removal TODO

S001: performance practice out of scope.

## Constants (`shared/constants.py`)
- [ ] 1. Remove `INEQUALITY_RATIOS`
- [ ] 2. Remove `VALID_INEQUALITY_LEVELS`

## Builder types (`builder/types.py`)
- [ ] 3. Remove `inequality: str` from `RhythmicProfile`
- [ ] 4. Remove `inequality_ratio: Fraction` from `GapRhythm`

## Rhythmic gap planner (`planner/rhythmic_gap.py`)
- [ ] 5. Remove `INEQUALITY_RATIOS` import and `_MAX_INEQUALITY_VALUE`
- [ ] 6. Remove `apply_inequality` function
- [ ] 7. Remove inequality call and ratio in `derive_gap_rhythm`

## Rhythmic profile loader (`planner/rhythmic_profile.py`)
- [ ] 8. Remove `VALID_INEQUALITY_LEVELS` import
- [ ] 9. Remove inequality validation
- [ ] 10. Remove inequality from profile construction

## Affect profiles YAML (`data/rhythm/affect_profiles.yaml`)
- [ ] 11. Remove `inequality:` from all entries

## Comments cleanup
- [ ] 12. Update comments in `rhythmic.py`, `rhythmic_gap.py`, `rhythm_templates.yaml`

## Log
- [ ] 13. Log to completed.md
