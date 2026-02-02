# Phase 5 continuation: MIDI elimination question

## Context

You are continuing a design session for the Andante baroque composition system.  Read these files in order before responding:

1. `CLAUDE.md` — project rules and conventions
2. `docs/Tier1_Normative/laws.md` — design laws
3. `docs/Tier2_Architecture/architecture.md` — system architecture
4. `revision_plan.md` — the 9-phase revision plan
5. `phase5_design.md` — the VoicePlan contract (just written)
6. `phase5_prompt.md` — original problem statement (for background)
7. `builder/types.py` — current type definitions (Anchor has upper_midi/lower_midi fields)
8. `builder/figuration/types.py` — Figure, FiguredBar, SelectionContext
9. `shared/key.py` — Key class with degree_to_midi, diatonic_step

All paths relative to `D:/projects/Barok/barok/source/andante/`.

## What was decided

phase5_design.md introduces:

- **DiatonicPitch** — a linear integer counting diatonic steps.  No mod-7 wrapping.  Eliminates all octave-ambiguity bugs.  `degree` and `octave` are derived properties.
- **VoicePlan contract** — frozen dataclass hierarchy (CompositionPlan → VoicePlan → SectionPlan → GapPlan).  Every compositional decision lives in the plan.  The writer makes zero compositional choices.
- **WritingMode enum** — FIGURATION, CADENTIAL, PILLAR, STAGGERED, WALKING (future), ARPEGGIATED (future).
- **Figure degrees become signed offsets** from anchor's DiatonicPitch.step, not unsigned 1-7.
- **MIDI becomes derived** — `Key.diatonic_to_midi(dp: DiatonicPitch) -> int` replaces stored MIDI on anchors.

## The question

With DiatonicPitch as the internal representation, should MIDI be eliminated entirely from the internal pipeline?  Currently:

- Anchor carries `upper_midi` and `lower_midi` (set by `place_anchors_in_tessitura`)
- `selector.py` uses MIDI for cross-relation and parallel-motion checks (`_degree_to_semitone_approx` is a hack that approximates MIDI from degrees)
- `figurate.py` passes `soprano_start_midi` and `bass_start_midi` to filters
- `FiguredBar` stores degrees, not MIDI — realisation converts at the end
- Output (MIDI file, MusicXML) needs MIDI at the very end

The question: in the new design, does MIDI exist only at the output boundary?  Or is there a legitimate internal use that DiatonicPitch cannot serve?

Think about:
- Cross-relation detection (needs chromatic intervals — semitones)
- Parallel fifth/octave detection (needs interval quality — perfect vs imperfect)
- Range checking (actuator range is currently MIDI)
- Tessitura placement (currently assigns MIDI to anchors)
- Key.diatonic_step currently works in MIDI space

If MIDI is eliminated internally, what replaces it for chromatic-interval checks?  Does DiatonicPitch + Key give enough information, or do we need a ChromaticPitch companion?

Deliver verdict first, then rationale.
