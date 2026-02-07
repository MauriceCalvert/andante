# Playability Validation

## Overview

Universal model for validating whether a bar of music is playable on a given instrument. Returns pass/fail, not fingering suggestions.

## Core Concepts

**Stave** — Unit of generation and validation. Maps to exactly one actuator. What a performer reads.

**Actuator** — Physical mechanism (bow, hand, breath). Has constraints. What instrument file defines.

**Voice** — Internal bookkeeping within a stave. Used for voice leading, fugue tracking, stem direction. Not relevant to playability validation.

```
Score definition       Stave              Instrument
----------------       -----              ----------
stave: flute       ──► notes at time T ──► actuator: breath ──► playable?
stave: keyboard_rh ──► notes at time T ──► actuator: right_hand ──► playable?
stave: keyboard_lh ──► notes at time T ──► actuator: left_hand ──► playable?
```

## Design Principles

1. **Stave-driven** — Each stave validates independently against its actuator
2. **Instrumentation first** — Instruments known before generation; generation respects actuator range
3. **Consistent grammar** — Same constraint types across all instruments, different parameter values

## Score Definition

Score maps staves to instruments and actuators:

```yaml
staves:
  - name: flute
    instrument: flute_concert
    actuator: breath
    
  - name: keyboard_rh
    instrument: keyboard
    actuator: right_hand
    
  - name: keyboard_lh
    instrument: keyboard
    actuator: left_hand
```

Keyboard fugue: 2 staves (RH may contain 2 polyphonic lines, validated together).
Trio sonata: 3 staves (violin1, violin2, continuo).

## Instrument Definition

Instrument files define actuator capabilities only:

```yaml
name: instrument_name

actuators:
  - name: actuator_name
    range: [min, max]              # MIDI pitch bounds
    available_pitches: [...]       # optional, overrides range (natural horn, etc.)
    max_simultaneous: n            # notes at once
    max_leap: semitones            # melodic interval limit
    reach:                         # simultaneous note constraints
      method: monophonic | span | strings
      # method-specific parameters
```

## Reach Methods

### monophonic

Single-note instruments (recorder, trumpet, oboe, voice).

```yaml
reach:
  method: monophonic
```

Validation: `max_simultaneous` must be 1.

### span

Fixed maximum interval between simultaneous notes (keyboard hands).

```yaml
reach:
  method: span
  span: 12             # octave
```

Validation: `max(notes) - min(notes) <= span`

### strings

Fretted/unfretted string instruments. Notes must be on playable string combination from same hand position.

```yaml
reach:
  method: strings
  strings:
    G: 55
    D: 62
    A: 69
    E: 76
  max_position: 10                 # semitones above open
  finger_reach: [0, 2, 3, 5]       # semitones from position base
  combinable: [[G, D], [D, A], [A, E]]   # which strings can sound together
  max_gap: 1                       # string skip limit (gamba may allow 2)
```

Validation algorithm:
1. For each note, find which strings can play it (note >= open, note <= open + max_position + max(finger_reach))
2. Find assignment of notes to strings where all strings are combinable
3. Check position compatibility: all notes reachable from same position

### Position compatibility check

```
position_compatible(notes_with_strings):
    for position in 0..max_position:
        all_reachable = true
        for (note, string) in notes_with_strings:
            offset = note - strings[string]
            reachable = any(offset == position + f for f in finger_reach)
            if not reachable:
                all_reachable = false
                break
        if all_reachable:
            return true
    return false
```

## Validation Algorithm

```
validate_bar(bar, score):
    for stave in score.staves:
        actuator = load_actuator(stave.instrument, stave.actuator)
        stave_notes = bar.notes_for_stave(stave.name)
        
        if not validate_actuator(stave_notes, actuator):
            return false
    
    return true

validate_actuator(notes, actuator):
    # Check range
    for note in notes:
        if note.pitch < actuator.range[0]: return false
        if note.pitch > actuator.range[1]: return false
        if actuator.available_pitches:
            if note.pitch not in actuator.available_pitches: return false
    
    # Check simultaneous constraints at each instant
    for instant in all_attack_times(notes):
        sounding = notes_at(notes, instant)
        if len(sounding) > actuator.max_simultaneous: return false
        if not check_reach(sounding, actuator.reach): return false
    
    # Check melodic constraints (transitions)
    for (prev, curr) in consecutive_note_pairs(notes):
        leap = abs(curr.pitch - prev.pitch)
        if leap > actuator.max_leap: return false
    
    return true

check_reach(notes, reach):
    if reach.method == 'monophonic':
        return len(notes) <= 1
    
    if reach.method == 'span':
        if len(notes) <= 1: return true
        return max(n.pitch for n in notes) - min(n.pitch for n in notes) <= reach.span
    
    if reach.method == 'strings':
        return exists_valid_string_assignment(notes, reach)
```

## Baroque Instrument Coverage

| Instrument | Actuators | Reach Method | Notes |
|------------|-----------|--------------|-------|
| Violin | 1 (bow) | strings | 4 strings, adjacent combinable |
| Viola | 1 (bow) | strings | 4 strings, adjacent combinable |
| Cello | 1 (bow) | strings | 4 strings, adjacent combinable |
| Viola da gamba | 1 (bow) | strings | 6 strings, max_gap: 1 or 2 |
| Lute | 1 (hand) | strings | 6+ courses, wider combinations |
| Harpsichord | 2 (hands) | span | Two manuals irrelevant for playability |
| Clavichord | 2 (hands) | span | |
| Organ | 2 (hands) + 1 (pedal) | span | Three actuators |
| Recorder | 1 (breath) | monophonic | |
| Oboe | 1 (breath) | monophonic | |
| Bassoon | 1 (breath) | monophonic | |
| Flute | 1 (breath) | monophonic | |
| Natural horn | 1 (breath) | monophonic | Uses available_pitches |
| Natural trumpet | 1 (breath) | monophonic | Uses available_pitches |
| Voice | 1 (breath) | monophonic | Range varies by part |

## Future Enhancements

### Transition Time

Some leaps require minimum time to execute (position shifts, hand crossing):

```yaml
transition_time:
  7: 0.125    # fifth needs eighth note minimum
  12: 0.25   # octave needs quarter note
```

### Breath and Articulation

Wind instruments and voice have phrase-level constraints:

- **Breath** — Maximum phrase length without rest, minimum rest duration to breathe
- **Tonguing** — Maximum repeated-note speed, articulation patterns (double/triple tonguing)
- **Lip fatigue** — Brass instruments, sustained high register

```yaml
breath:
  max_phrase_beats: 8
  min_rest_beats: 0.5

tonguing:
  max_repeated_per_beat: 4
```

### Lute and Theorbo

Plucked strings with special characteristics:

- **Courses** — Paired strings tuned in unison or octaves, count as single note
- **Unfrettable basses** — Theorbo bass strings can only play open pitches
- **Variable tuning** — Different tunings affect available pitches

### Organ Pedals

Third actuator with distinct constraints:

- **Limited range** — Typically C2-F4
- **Limited agility** — Slower than hands, larger leap penalty
- **One note typical** — max_simultaneous: 1 or 2

### Sackbut

Slide positions constrain transitions:

- **Seven positions** — Like string positions but discrete
- **Position change time** — Large position jumps need more duration
- **Same-position preference** — Notes playable in same position are easier in sequence

### Harp Pedals

Stateful pitch constraints:

- **Pedal state** — Each pitch class has setting (flat/natural/sharp)
- **No simultaneous variants** — Cannot play C and C# at same instant
- **Change time** — Pedal switch requires gap between conflicting pitches

## Integration

Playability validation runs after L8 Melodic produces concrete pitches. Failed validation triggers backtracking to L7 Figuration (choose different pattern) or L4 Seed (choose different schema).

Note: L7 Figuration and L8 Melodic are historical layers, superseded by phrase-level generation in the current architecture (L6 Phrase Writing). See architecture.md v2.0.0.
