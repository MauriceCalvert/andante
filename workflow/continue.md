# Continue: Post-INV

## Current state (2026-02-14)

**INV complete.** All three phases implemented and passing:
- INV-1: Countersubject in all subject entries ✓
- INV-2: Episodes from subject fragments ✓
- INV-3: Stretto in peroratio ✓

**Stretto bug fixed.** CC's original peroratio YAML (passo_indietro +
cadenza_composta = 3 bars) was too short for stretto. Fixed by
prepending fenaroli (4 bars) to the peroratio schema_sequence.
Also fixed stretto tail crash: voice A gap-zone pad + galant-order
tail generation (structural soprano → bass → Viterbi soprano).

**Brief fallback law added.** When a composition falls back because
the genre YAML or brief made something impossible, `brief_warning()`
from `shared/errors.py` emits a kind sarcastic warning with
what_failed, why, and suggestion. Algorithmic fallbacks (Viterbi
soft-only, stepwise fill) are normal runtime and do NOT use this.
Four sites converted.

**Listening gate pending.** Maurice needs to listen to
`output/invention_c_major.midi` to confirm INV sounds right.

## What to do next

See `workflow/todo.md` for full list. Next candidates:
1. Exordium answer gap (invention YAML only has one non-cadential
   phrase in exordium — answer+CS never fires)
2. Structural knot consonance — tritones between voice knots
3. VG4 — Rewrite phrase_writer composition order
4. VG5 — Style as weights from YAML

## Read at chat start

- `workflow/conductor.md` (always)
- `docs/Tier1_Normative/laws.md`
- `docs/knowledge.md`
- `completed.md`
- `workflow/todo.md`
- This file
