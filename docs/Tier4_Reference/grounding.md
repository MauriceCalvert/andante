# Andante Grounding

## Overview

This document identifies the musicological foundations underlying the Andante planning system. All design decisions should be traceable to historical practice or scholarly analysis.

## Primary Sources

### Johann Mattheson — *Der vollkommene Capellmeister* (1739)

**Contribution:** Affektenlehre (doctrine of affects), key characteristics

The idea that music expresses specific emotions, and that compositional choices flow from the intended affect. Mattheson catalogued affects and their musical characteristics. He also described the character of different keys (e.g., D major as sharp and obstinate, F major as tender).

**Influence on Andante:**
- `Brief.affect` as the primary compositional input
- affects.yaml mapping affect → tempo, mode, key character
- Key characters (dark/bright) as simplified key-affect associations
- Affect governs downstream decisions (arc selection, material character)

### Heinrich Christoph Koch — *Introductory Essay on Composition* (1782-1793)

**Contribution:** Phrase structure, punctuation theory, and deceptive motion

Koch described musical phrases as analogous to linguistic sentences, with cadences serving as punctuation marks of varying strength. He also discussed "parentheses" and deceptive progressions as means of extending and surprising.

**Influence on Andante:**
- Cadence hierarchy: `authentic` (full stop), `half` (comma), `deceptive` (interrupted)
- Phrase as the fundamental planning unit
- `Section.final_cadence` determining section closure strength
- Surprise types: `evaded_cadence`, `early_return` as planned deviations

### Joseph Riepel — *Anfangsgründe zur musicalischen Setzkunst* (1752-1768)

**Contribution:** Phrase function and tonal motion

Riepel identified stereotypical tonal motions (Monte, Fonte, Ponte) and phrase types with characteristic functions.

**Influence on Andante:**
- `Phrase.tonal_target` as Roman numeral
- `Section.tonal_path` as a journey through keys
- Phrase functions: opening, continuation, cadential (implicit in arc treatments)

### Robert Gjerdingen — *Music in the Galant Style* (2007)

**Contribution:** Schema theory

Gjerdingen codified galant schemata as stock patterns with specific soprano/bass scale-degree skeletons. Schemata are combinatorial building blocks.

**Influence on Andante:**
- **Not directly used in planner** — schemata are execution vocabulary
- Planner specifies phrase function and tonal target; executor selects appropriate schema
- This separation follows Gjerdingen's insight that schemata serve functions, not vice versa

**Partita (executor prototype) uses:**
- SchemaDefinition with soprano/bass degree sequences
- Schema sequencing grammar (follows/followed_by)
- Position categories (opening, continuation, transition, cadence)

### Leonard Ratner — *Classic Music: Expression, Form, and Style* (1980)

**Contribution:** Topic theory

Ratner identified musical topics (march, hunt, pastoral, etc.) as conventional signs carrying extra-musical meaning.

**Influence on Andante:**
- `Brief.genre` implies topical associations
- Affects carry gestural implications (maestoso → dotted rhythms, etc.)
- Deferred: explicit topic vocabulary for v2

### William Caplin — *Classical Form* (1998)

**Contribution:** Formal function theory

Caplin refined phrase function into tight-knit vs. loose-knit, presentation vs. continuation, and intrinsic vs. contextual function.

**Influence on Andante:**
- `Phrase.treatment`: statement, sequence (presentation functions)
- Deferred: inversion, fragmentation (continuation functions) for v2
- Arc structure implies Caplin's formal trajectory (stability → instability → resolution)

## Secondary Sources

### Johann Philipp Kirnberger — *The Art of Strict Musical Composition* (1771-1779)

**Contribution:** Voice leading and counterpoint rules

**Influence:** Executor, not planner. Planner assumes material can be realised correctly.

### C.P.E. Bach — *Essay on the True Art of Playing Keyboard Instruments* (1753-1762)

**Contribution:** Affect expression, ornamentation, improvisation

**Influence:** Execution details (ornaments, dynamics); planner deals with structure only.

### Partimento Tradition (Fedele, Durante, etc.)

**Contribution:** Rule of the octave, bass patterns, schema completion

**Influence:** Executor. Planner provides harmonic targets; executor realises via partimento principles.

## Design Traceability

| Andante Concept | Source | Citation |
|-----------------|--------|----------|
| Affect-driven planning | Mattheson | *Capellmeister* Part II, Ch. 3 |
| Key character (dark/bright) | Mattheson | *Capellmeister* Part II, Ch. 2 |
| Cadence as punctuation | Koch | *Introductory Essay* Vol. II |
| Surprise/deviation | Koch | *Introductory Essay* on parentheses |
| Tonal path | Riepel | *Anfangsgründe* Ch. 2-3 |
| Phrase function | Caplin | *Classical Form* Ch. 2 |
| Schema as execution unit | Gjerdingen | *Galant Style* Ch. 1-3 |
| Arc/dramatic shape | Mattheson | *Capellmeister* on rhetorical disposition |
| Statement/sequence treatments | Caplin | *Classical Form* Ch. 3 |

## Principles Derived from Sources

### From Mattheson

> "The composer must first decide what affect he wishes to arouse."

**Principle:** Affect precedes all other decisions. Brief.affect is the root of the planning tree.

### From Koch

> "The cadence is to music what punctuation is to speech."

**Principle:** Cadence hierarchy structures the piece. Not all stops are equal.

### From Riepel

> "The bass must make a journey."

**Principle:** Static harmony is death. Tonal path must move and return.

### From Gjerdingen

> "Schemata are building blocks, not straitjackets."

**Principle:** Planning specifies function; execution chooses realisation. Don't over-specify.

### From Caplin

> "Function is contextual, not intrinsic."

**Principle:** The same material (treatment) can serve different functions depending on placement. Arc placement matters.

## Out of Scope (Executor Concerns)

The following are grounded in the same sources but belong to execution, not planning:

- Voice leading rules (Kirnberger)
- Specific schema selection (Gjerdingen)
- Diminution and figuration (C.P.E. Bach)
- Rule of the octave (Partimento)
- Ornament placement (C.P.E. Bach)

## Future Grounding (v2+)

| Concept | Source | Notes |
|---------|--------|-------|
| Topics | Ratner | Explicit topic vocabulary |
| Minor mode | Mattheson, Koch | Affect-mode relationships |
| Rhetoric sections | Mattheson | Exordium, narratio, confirmatio, peroratio |
| Development techniques | Caplin | Fragmentation, liquidation |
| Countersubject | Marpurg | *Abhandlung von der Fuge* |

## References

- Caplin, William. *Classical Form: A Theory of Formal Functions for the Instrumental Music of Haydn, Mozart, and Beethoven*. Oxford University Press, 1998.
- Gjerdingen, Robert. *Music in the Galant Style*. Oxford University Press, 2007.
- Koch, Heinrich Christoph. *Introductory Essay on Composition*. Trans. Nancy Baker. Yale University Press, 1983 [1782-1793].
- Mattheson, Johann. *Der vollkommene Capellmeister*. Trans. Ernest Harriss. UMI Research Press, 1981 [1739].
- Ratner, Leonard. *Classic Music: Expression, Form, and Style*. Schirmer, 1980.
- Riepel, Joseph. *Anfangsgründe zur musicalischen Setzkunst*. 1752-1768.
