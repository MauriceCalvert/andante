# Phase 5 Prompt: VoicePlan Contract Design

Paste this entire prompt into a new Claude chat.

---

## Context

You are helping design a baroque music composition system called Andante. Read CLAUDE.md first, then all docs it references. Then read `docs/Tier2_Architecture/revision_plan.md` for the full context of what we're doing and why.

We are executing a surgical rebuild of the builder layer (the part that turns a compositional plan into actual notes). The planner (which decides *what* to compose) is sound. The builder (which executes those decisions) is broken because it makes compositional decisions that belong upstream.

The fix: every compositional decision must arrive in an explicit data structure — the **VoicePlan** — so the builder is purely mechanical.

This chat is dedicated to designing that contract.

## The Problem

Currently the builder's figuration engine (176KB, 18 files) infers context to make decisions:

- Detecting parallel fifths/octaves between voices it's writing simultaneously
- Checking for dissonances after placing notes
- Choosing hemiola based on bar position
- Deciding whether we're approaching a cadence
- Calculating density and character from affect config
- Selecting anacrusis, figures, junctions based on schema context
- Adapting output based on texture assignments
- Creating compound figures based on what "sounds right"

All of these must instead arrive as pre-made decisions in the VoicePlan.

## What the VoicePlan Must Replace

Read these files to understand what the builder currently infers:

- `builder/figuration/bar_context.py` (10KB) — computes bar function, beat class, harmonic tension, density, hemiola, overdotting, anacrusis, texture. **All of this should be in the plan.**
- `builder/figuration/strategies.py` (10KB) — selects figuration profile and strategy per schema. **Should be in the plan.**
- `builder/figuration/selector.py` (24KB) — filters figures by direction, tension, character, density, compensation, minor safety, note count, cross relation, parallel/direct motion. **Filtering by prior voices stays in the writer. Everything else should be in the plan.**
- `builder/figuration/figurate.py` (32KB) — the main engine. **Study what decisions it makes per bar and per anchor.**
- `builder/figuration/phrase.py` (3KB) — phrase position, deformation. **Should be in the plan.**
- `builder/types.py` — PassageAssignment, FiguredBar, etc. **Understand current data shapes.**

Also read:
- `docs/Tier2_Architecture/figuration.md` — the figuration design spec
- `docs/Tier2_Architecture/voices.md` — the voice entity model
- `docs/Tier2_Architecture/architecture.md` — the 7-layer pipeline

## Design Requirements

1. **One VoicePlan per voice.** The planner produces a VoicePlan for each voice in composition order.

2. **Per-bar granularity.** Most decisions vary bar by bar (density can change, cadence approach is bar-specific, hemiola applies to specific bars).

3. **The writer must make zero compositional decisions.** It receives the VoicePlan and executes mechanically. The only "decision" the writer makes is selecting the best figure from a pre-filtered candidate set — and even the filtering criteria (direction, tension level, character, density) come from the plan.

4. **Prior-voice awareness stays in the writer.** The writer sees previously-written voices and filters candidates to avoid parallel fifths/octaves and dissonances. This is the one thing that *cannot* be pre-planned because it depends on the actual notes written. But the plan must ensure feasibility (the anchor pairs and strategies must guarantee that legal options exist).

5. **Frozen dataclass.** VoicePlan and its components must be frozen dataclasses. No mutation.

6. **Voice-agnostic.** The VoicePlan doesn't know if it's for "soprano" or "bass." It knows the voice's role (schema_upper, schema_lower, imitative, harmony_fill), its actuator range, and its writing strategy.

7. **Strategy per section, not per piece.** A voice might use sustained strategy in the exordium and contrapuntal in the narratio. The plan specifies this per section or per bar range.

## What I Need From You

Design the VoicePlan data structure. Specifically:

1. The top-level VoicePlan type and its fields.
2. The per-bar (or per-section) decision structure.
3. The WritingStrategy enum or type.
4. How cadence approach, hemiola, anacrusis, density, character, and figure vocabulary are represented.
5. How the composition order (dependency graph) is represented.
6. How the plan connects to anchors (which are already produced by the metric layer).

Produce frozen dataclass definitions with type hints and single-line docstrings. Discuss trade-offs. Challenge anything that seems wrong.

Do not write implementation code. Design the types and the contract only.

## Rules

- Read CLAUDE.md first, then all docs it references.
- Verdict first, rationale second.
- No filler.
- Ask if unclear, don't guess.
- One class per file, methods alphabetical.
- Type-hint everything.
- Frozen dataclasses.
- No Greek symbols.
- Challenge my assumptions.
