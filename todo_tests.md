# Test Coverage Plan

## Steps
- [x] 1. `test_voice_checks.py` — parametrised tests for all public functions in voice_checks.py (64 passed)
- [x] 2. `test_music_math.py` — tests for fill_slot, is_valid_duration, VALID_DURATIONS (43 passed)
- [x] 3. `test_key.py` — tests for Key.diatonic_step, Key.midi_to_degree, Key.degree_to_midi, Key.midi_to_diatonic (48 passed)
- [x] 4. `test_compose_voices.py` — tests for compose_voices path (gap scheduler, interleaving, lead ordering) (9 passed)
- [x] 5. Rewrite test_L6_phrase_writer.py — parametrise over all 8 genres × all schemas (1426 passed, 207 skipped, 38 xfailed, 31 xpassed)

## Known bugs exposed by step 5
- S-11: phrase_writer stepwise fill repeats pitch across bar boundary when soprano target unchanged (18 xfails, all 4/4 genres)
- CP-04: phrase_writer bass structural tone forms tritone/dissonance with soprano at bar start (20 xfails, all genres)
