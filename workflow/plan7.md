# Plan 7 — Additional Genres for Validation

## Problem

Plans 1–6 have been developed and tested on two genres: minuet (3/4)
and gavotte (4/4). The system has genre configs for six more genres
(bourree, chorale, fantasia, invention, sarabande, trio_sonata) but
it is unknown whether the pipeline produces musically acceptable
output for any of them. Each genre has a distinct character that
tests different aspects of the system:

- **Sarabande** (3/4, slow): sustained bass, ornamental soprano,
  emphasis on beat 2. Tests whether the system can produce slow,
  weighted music rather than just flowing lines.
- **Bourree** (4/4, fast, quarter-note upbeat): energetic walking
  bass, brisk character. Tests upbeat handling and fast walking bass.
- **Invention** (4/4, contrapuntal): both voices are melodically
  active. Tests walking-bass quality when the bass is not
  subordinate but an equal contrapuntal voice.

## Musical Goal

- At least two additional genres produce output that sounds like
  the named dance/form, not like a generic piece that happens to
  be in the right metre.
- Genre-specific character is audible: a sarabande sounds stately
  and weighted, a bourree sounds brisk and propulsive, an invention
  sounds like two voices in dialogue.
- Faults do not increase beyond the baseline established for minuet
  and gavotte.

## Phases

### Phase 7.1 — Sarabande validation

**What to do:** Run the pipeline for sarabande. Evaluate the output
as Bob, then diagnose as Chaz.

**Key questions for Bob:**
- Does beat 2 carry weight, or does it sound like an ordinary 3/4?
- Does the bass sound sustained, or does it walk/bounce?
- Is the soprano ornamental or plain?
- Does the tempo feel slow and stately?

**Expected issues:**
- `bass_pattern: continuo_sustained` may not be implemented or may
  fall through to pillar. Verify.
- Rhythm cells for sarabande exist (3/4 cells tagged `sarabande`)
  but they may not capture the beat-2 emphasis.
- The `ornate` character in section B may not produce different
  figuration from `expressive` in section A.

**Scope:** Pipeline run + analysis. Code fixes only if the genre
config or a code path is broken (crash or wrong texture). Musical
refinement of sarabande character is a follow-up, not this phase.

**Acceptance:** The pipeline completes without error. Bob identifies
at least one sarabande-specific character trait in the output. If
the output sounds generic, document what is missing.

### Phase 7.2 — Bourree validation

**What to do:** Run the pipeline for bourree. Evaluate.

**Key questions for Bob:**
- Does the upbeat (quarter note) land correctly?
- Does the bass walk energetically, or plod?
- Does the tempo feel brisk?
- Is there a contrast between sections A and B?

**Expected issues:**
- `bass_pattern: continuo_walking` routes to walking bass, which
  should now have even note values (Plan 4). Verify.
- The quarter-note upbeat (`upbeat: "1/4"`) must be handled
  correctly in bar-offset arithmetic.
- Fast tempo (90 bpm) with walking bass in quarter notes may
  produce too many notes per bar for the bass to sound grounded.

**Scope:** Pipeline run + analysis. Fix crashes or config errors.

**Acceptance:** The pipeline completes. The upbeat is correctly
placed. Walking bass produces even quarter notes at the right tempo.

### Phase 7.3 — Invention validation

**What to do:** Run the pipeline for invention. Evaluate.

**Key questions for Bob:**
- Do both voices sound melodically active?
- Is there any sense of imitative dialogue, or do the voices
  sound unrelated?
- Does the through-composed form feel like a continuous argument,
  or a sequence of disconnected episodes?
- Does the walking bass texture in the narrative section produce
  a genuine contrapuntal line?

**Expected issues:**
- The invention genre config has `bass_treatment: contrapuntal`,
  which may not be implemented. Check what the pipeline does with
  an unrecognised bass_treatment.
- `lead_voice` alternation (0 in exordium, 1 in narratio) may
  not be wired into the soprano/bass dispatch.
- Through-composed form may not chain schemas differently from
  binary form.
- The IMITATIVE voice role is defined but not wired.

**Scope:** This is likely the most broken genre. The goal is not to
make inventions work fully — that requires imitative counterpoint,
which is a major feature. The goal is to identify what breaks, what
falls back gracefully, and what needs architectural work.

**Acceptance:** The pipeline completes (possibly with fallbacks).
A clear list of what works, what falls back, and what is missing
for inventions to sound like inventions.

### Phase 7.4 — Genre comparison summary

**What to do:** Compile a comparison table across all tested genres:

| Genre | Metre | Completes? | Faults | Genre character audible? | Key gaps |
|-------|-------|------------|--------|------------------------|----------|

This summary becomes the input for deciding what to work on next
after Plan 7.

**Acceptance:** The table is complete and honest. "Genre character
audible" is a yes/no judgment from Bob, not a fault count.

## Out of Scope

- Chorale (homophonic, needs inner voices — parked).
- Fantasia (free form, needs different structural approach).
- Trio sonata (three voices, needs third voice infrastructure).
- Making any genre "good." This plan is validation and triage, not
  refinement. The output is a prioritised list of what each genre
  needs, not working genres.
