# Thematic Design

## Principle

The entry sequence is data, not logic. A genre YAML file lists every
thematic entry in order. Each entry specifies, for each voice, what
material to play and in what key. The planner reads top to bottom,
assigns bars, inserts episodes where key distance requires them, and
appends a cadence. That is the entire piece plan.

## Entry sequence format

```yaml
entry_sequence:
  - upper: [subject, I]
    lower: none
  - upper: [cs, I]
    lower: [answer, V]
  - upper: [subject, vi]
    lower: [cs, vi]
  - upper: [cs, IV]
    lower: [subject, IV]
  - upper: [subject, V]
    lower: [cs, V]
  - upper: [cs, I]
    lower: [subject, I]
  - upper: [stretto, I]
    lower: [stretto, I]
  - cadence
```

### Voice slots

Each entry has two voice slots: `upper` and `lower`. Each slot is one of:

- `[material, key]` — render material in that key
- `none` — voice is silent (rests)

### Material types

| Material   | Source                        | Meaning                          |
|------------|-------------------------------|----------------------------------|
| `subject`  | .subject subject degrees        | Subject statement                |
| `answer`   | .subject answer degrees         | Answer (subject at the dominant) |
| `cs`       | .subject countersubject degrees | Countersubject                   |
| `stretto`  | .subject subject degrees × 2   | Both voices state subject with delay |

### Key labels

Key labels are Roman numerals relative to home key: `I`, `V`, `IV`,
`vi`, `iii`, `ii`. Resolved at render time via `home_key.modulate_to()`.

The answer material has its own built-in transposition (the .subject file
encodes the dominant-level degrees). The key label tells the renderer
which key context to place the answer in, not which interval to
transpose by. So `[answer, V]` means "render the pre-composed answer
form, rooted on the dominant of home_key."

### `none`

Bare `none`. No key, no material. The voice rests for the duration of
the entry. Used for monophonic openings.

### `cadence`

Final line. Rendered by cadence_writer using existing clausula templates.

## Entry duration

Each entry occupies `subject.bars` bars (from the .subject file). For
call_response.subject that is 2 bars. The subject, answer, and CS all
have the same duration by construction.

## Episodes

Episodes are not specified in the YAML. They are inserted automatically
by the subject planner at **section boundaries** — the gaps between
exposition, development, and recapitulation. They are developmental
passages, not gap-fillers; they exist because the ear has heard the
subject and now wants to hear what can be done with it.

**Where:** between sections only. Not between consecutive entries
within the same section. The entry_sequence comments mark section
boundaries explicitly.

**Exposition exemption:** the transition from I to V within the
exposition is not an episode trigger. The tonal answer itself handles
this key shift — the 1↔5 mutation is built into the answer material.
This is a definitional property of the exposition, not a distance
calculation.

**Trigger:** key distance between the last entry of one section and
the first entry of the next section. The planner measures
tonic-to-tonic distance (e.g. G major → A minor is one diatonic step;
F major → G major is one step; G major → C major is a fourth).

**Decision:** key distance determines episode *length and direction*,
not whether an episode exists. All section boundaries get an episode.
Short distances get short episodes (2 bars); larger distances get
longer ones (3–4 bars).

**Content:** head fragment from the subject, sequenced diatonically
downward (or upward) through intermediate scale degrees. This is
derived material, not Viterbi fill.

**Direction:** determined by the key relationship. If the next section
is lower, the sequence descends. If higher, it ascends.

**Voicing:** episode lead voice defaults to the opposite of the
preceding entry's lead voice (the voice that played subject or answer),
so the fragment hands off naturally to the next entry.

**The piece length** falls out of the data: (number of entries ×
subject bars) + episode bars + cadence bars. There is no hardcoded
bar count.

## What the planner does

1. Read entry_sequence from genre YAML
2. Walk entries top to bottom, bar pointer starting at 1
3. For each entry:
   a. Check key distance from previous entry
   b. If distance requires bridging, insert episode bars, advance pointer
   c. Stamp entry at current bar, advance pointer by subject.bars
4. Append cadence
5. Total bars = final bar pointer

The planner does not:
- Alternate voices by even/odd logic
- Swap voices based on entry_count
- Reference lead_voice from section config
- Use schemas to determine what is an entry vs episode

## What the renderer does

For each entry, the renderer reads the voice slots and calls:
- `subject_to_voice_notes()` for subject material
- `answer_to_voice_notes()` for answer material (new function, uses .subject answer data)
- `countersubject_to_voice_notes()` for CS material
- Stretto handler for stretto entries
- Nothing for `none` slots (voice rests)

The key label is resolved to a Key object and passed to the renderer
for correct transposition and octave placement.

## Relation to schemas

Schemas handle harmony underneath. The entry sequence handles thematic
material on top. They are independent layers. The planner may assign
schemas to bars for harmonic grounding, but the entry sequence does not
know or reference schema names.

## Relation to sections

Sections (exordium, narratio, etc.) are rhetorical labels. They do not
drive voice assignment or entry placement. The entry_sequence replaces
per-section lead_voice, invertible_counterpoint, and min_non_cadential.

## Current bugs this design fixes

1. **No monophonic opening.** Entry 1 has `lower: none`.
2. **Answer never rendered.** Entry 2 has `lower: [answer, V]`.
3. **Voice alternation dead.** No alternation logic. The YAML says
   exactly who plays what.
4. **Key contrast absent.** Each entry specifies its key explicitly.
5. **Double alternation cancellation.** Eliminated — no lead_voice ×
   entry_count interaction.
