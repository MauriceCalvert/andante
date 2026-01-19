# Brief & Genre Upgrade for Schema-First Planning

## Principle

**Brief = commission (what), Genre = style template (how)**

The brief remains a simple user intent. Genre files encode all schema-first expertise. The planner merges them:

```
Brief (user wants) + Genre (style knowledge) → Planner → Plan
```

## Current State

### Brief Format
```yaml
brief:
  affect: Freudigkeit
  genre: invention
  forces: keyboard
  bars: 24
frame:
  key: C
  mode: major
  metre: 4/4
  tempo: allegro
material:
  subject:
    file: motifs/library/surprise.subject
```

### Genre Format (invention.yaml)
```yaml
voices: 2
metre: 4/4
form: through_composed
arc: invention
treatment_constraints:
  must_include: [imitation, stretto]
sections:
  - label: A
    tonal_path: [I, V, iii, IV, V]
    final_cadence: half
    bars_per_phrase: 2
```

**Problem:** Genres use melody-first concepts (tonal_path, episodes, arc) incompatible with schema-first planning.

## New Format

### Brief (minimal change)

```yaml
# briefs/two_part_invention.brief
brief:
  affect: Freudigkeit
  genre: invention
  forces: keyboard
  bars: 16

frame:
  key: C
  mode: major
  metre: 4/4
  tempo: allegro

# Optional: provide subject for validation
# Omit to derive from opening schema
subject:
  degrees: [1, 2, 3, 4, 5]
  durations: [1/8, 1/8, 1/8, 1/8, 1/2]

# Optional: override genre defaults
overrides:
  schema_preferences:
    opening: [meyer]  # prefer Meyer instead of genre default
```

**Changes from current:**
1. `material.subject` → `subject` (top-level, simpler)
2. Remove `structure` section entirely (planner generates this)
3. Add optional `overrides` for fine control

### Genre (complete rewrite)

```yaml
# data/genres/invention.yaml
name: Two-Part Invention
voices: 2
metre: 4/4
texture: imitative

# Schema selection by formal position
# Keys match typical_position in schema_transitions.yaml
schema_preferences:
  opening:
    - romanesca       # weight 1.0 (default)
    - do_re_mi        # weight 1.0
  riposte:
    - prinner         # almost always prinner for inventions
  continuation:
    - fonte
    - monte
    - fenaroli
  pre_cadential:
    - passo_indietro
    - indugio
  cadential:
    - complete_cadence
    - half_cadence

# Cadence planning rules
cadence_template:
  density: high              # high = every 2-4 bars, medium = 4-8, low = 8+
  first_cadence_bar: 4       # typical first cadence location
  first_cadence_type: half   # usually half cadence
  section_end_type: half     # at section boundary
  final_type: authentic      # piece must end PAC on I

# Section structure
sections:
  - label: A
    key_area: I
    proportion: 0.5          # half the piece
    end_cadence: half        # ends on half cadence
  - label: B
    key_area: V              # moves to dominant area
    proportion: 0.5
    end_cadence: authentic   # final authentic cadence

# Subject constraints (for validation and derivation)
subject_constraints:
  min_notes: 4
  max_notes: 12
  max_bars: 2
  require_invertible: true   # must work in inversion
  require_answerable: true   # must work at fifth
  first_degree: [1, 3, 5]    # allowed starting degrees
  last_degree: [2, 3, 5, 7]  # avoid strong closure

# Treatment vocabulary for this genre
treatments:
  required: [statement, imitation]
  optional: [sequence, inversion, stretto]
  opening: statement         # first slot always statement
  answer: imitation          # second slot typically imitation
```

### Genre Files to Update

| Genre | Texture | Cadence Density | Typical Opening |
|-------|---------|-----------------|-----------------|
| invention | imitative | high (2-4 bars) | romanesca, do_re_mi |
| minuet | melody_bass | low (8 bars) | do_re_mi |
| gavotte | melody_bass | medium (4 bars) | romanesca |
| sarabande | melody_bass | low (8 bars) | romanesca, prinner |
| bourree | melody_bass | medium (4 bars) | romanesca |
| fantasia | mixed | variable | any |
| chorale | homophonic | low (phrase-end) | fenaroli |
| trio_sonata | imitative | medium | romanesca, do_re_mi |

## Type Changes

### In plannertypes.py

**Add:**
```python
@dataclass(frozen=True)
class GenreTemplate:
    """Schema-first genre specification."""
    name: str
    voices: int
    metre: str
    texture: str
    schema_preferences: dict[str, list[str]]
    cadence_template: CadenceTemplate
    sections: tuple[GenreSection, ...]
    subject_constraints: SubjectConstraints
    treatments: TreatmentSpec


@dataclass(frozen=True)
class CadenceTemplate:
    """Cadence planning rules."""
    density: str              # high, medium, low
    first_cadence_bar: int
    first_cadence_type: str
    section_end_type: str
    final_type: str


@dataclass(frozen=True)
class GenreSection:
    """Section template in genre."""
    label: str
    key_area: str
    proportion: float
    end_cadence: str


@dataclass(frozen=True)
class SubjectConstraints:
    """Rules for subject validation/derivation."""
    min_notes: int
    max_notes: int
    max_bars: int
    require_invertible: bool
    require_answerable: bool
    first_degree: tuple[int, ...]
    last_degree: tuple[int, ...]


@dataclass(frozen=True)
class TreatmentSpec:
    """Treatment vocabulary for genre."""
    required: tuple[str, ...]
    optional: tuple[str, ...]
    opening: str
    answer: str
```

**Modify Brief:**
```python
@dataclass(frozen=True)
class Brief:
    """User input specifying compositional intent."""
    affect: str
    genre: str
    forces: str
    bars: int
    key: str | None = None
    mode: str | None = None
    metre: str | None = None
    tempo: str | None = None
    subject: Motif | None = None           # optional subject
    overrides: dict | None = None          # optional genre overrides
```

**Remove from Brief:**
- `virtuosic` (unused)
- `motif_source` (replaced by `subject`)

## File Changes

### Create

| File | Purpose |
|------|---------|
| `planner/genre_loader.py` | Load and parse genre YAML into GenreTemplate |
| `planner/brief_parser.py` | Parse brief YAML, merge with genre |

### Modify

| File | Change |
|------|--------|
| `planner/plannertypes.py` | Add GenreTemplate, CadenceTemplate, etc. |
| `planner/planner.py` | Use genre_loader, new orchestration |
| `data/genres/*.yaml` | Rewrite all 8 files to new format |

### Delete

| File | Reason |
|------|--------|
| `data/arcs.yaml` | Arcs replaced by schema_preferences |
| `data/episode_constraints.yaml` | Episodes replaced by schemas |
| `data/fantasia_arcs.yaml` | Replaced by fantasia genre |

## Module: genre_loader.py

```python
"""Load genre templates from YAML."""
from pathlib import Path
import yaml
from planner.plannertypes import (
    GenreTemplate, CadenceTemplate, GenreSection,
    SubjectConstraints, TreatmentSpec,
)

DATA_DIR = Path(__file__).parent.parent / "data" / "genres"
_CACHE: dict[str, GenreTemplate] = {}


def load_genre(name: str) -> GenreTemplate:
    """Load genre template by name."""
    if name in _CACHE:
        return _CACHE[name]
    
    path = DATA_DIR / f"{name}.yaml"
    assert path.exists(), f"Unknown genre: {name}. File not found: {path}"
    
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    template = _parse_genre(data)
    _CACHE[name] = template
    return template


def _parse_genre(data: dict) -> GenreTemplate:
    """Parse genre dict into GenreTemplate."""
    return GenreTemplate(
        name=data["name"],
        voices=data["voices"],
        metre=data["metre"],
        texture=data["texture"],
        schema_preferences=data["schema_preferences"],
        cadence_template=_parse_cadence_template(data["cadence_template"]),
        sections=tuple(_parse_section(s) for s in data["sections"]),
        subject_constraints=_parse_constraints(data["subject_constraints"]),
        treatments=_parse_treatments(data["treatments"]),
    )


def _parse_cadence_template(data: dict) -> CadenceTemplate:
    """Parse cadence template."""
    return CadenceTemplate(
        density=data["density"],
        first_cadence_bar=data["first_cadence_bar"],
        first_cadence_type=data["first_cadence_type"],
        section_end_type=data["section_end_type"],
        final_type=data["final_type"],
    )


def _parse_section(data: dict) -> GenreSection:
    """Parse genre section."""
    return GenreSection(
        label=data["label"],
        key_area=data["key_area"],
        proportion=data["proportion"],
        end_cadence=data["end_cadence"],
    )


def _parse_constraints(data: dict) -> SubjectConstraints:
    """Parse subject constraints."""
    return SubjectConstraints(
        min_notes=data["min_notes"],
        max_notes=data["max_notes"],
        max_bars=data["max_bars"],
        require_invertible=data["require_invertible"],
        require_answerable=data["require_answerable"],
        first_degree=tuple(data["first_degree"]),
        last_degree=tuple(data["last_degree"]),
    )


def _parse_treatments(data: dict) -> TreatmentSpec:
    """Parse treatment specification."""
    return TreatmentSpec(
        required=tuple(data["required"]),
        optional=tuple(data.get("optional", [])),
        opening=data["opening"],
        answer=data["answer"],
    )
```

## Module: brief_parser.py

```python
"""Parse brief YAML and merge with genre."""
from fractions import Fraction
from pathlib import Path
import yaml
from planner.genre_loader import load_genre
from planner.plannertypes import Brief, Motif, GenreTemplate


def parse_brief(path: Path) -> tuple[Brief, GenreTemplate]:
    """Parse brief file and load its genre.
    
    Returns:
        (brief, genre_template) - genre may have overrides applied
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    brief = _parse_brief_data(data)
    genre = load_genre(brief.genre)
    
    # Apply overrides if present
    if brief.overrides:
        genre = _apply_overrides(genre, brief.overrides)
    
    return brief, genre


def _parse_brief_data(data: dict) -> Brief:
    """Parse brief section of YAML."""
    b = data["brief"]
    frame = data.get("frame", {})
    
    subject = None
    if "subject" in data:
        subject = _parse_subject(data["subject"])
    
    return Brief(
        affect=b["affect"],
        genre=b["genre"],
        forces=b["forces"],
        bars=b["bars"],
        key=frame.get("key"),
        mode=frame.get("mode"),
        metre=frame.get("metre"),
        tempo=frame.get("tempo"),
        subject=subject,
        overrides=data.get("overrides"),
    )


def _parse_subject(data: dict) -> Motif:
    """Parse subject into Motif."""
    if "file" in data:
        return _load_subject_file(data["file"])
    
    degrees = tuple(data["degrees"])
    durations = tuple(Fraction(d) for d in data["durations"])
    bars = sum(durations) // Fraction(1)  # approximate
    
    return Motif(
        degrees=degrees,
        durations=durations,
        bars=int(bars),
    )


def _load_subject_file(path: str) -> Motif:
    """Load subject from .subject file."""
    # Implementation depends on subject file format
    raise NotImplementedError("Subject file loading")


def _apply_overrides(genre: GenreTemplate, overrides: dict) -> GenreTemplate:
    """Apply brief overrides to genre template."""
    schema_prefs = dict(genre.schema_preferences)
    
    if "schema_preferences" in overrides:
        for position, schemas in overrides["schema_preferences"].items():
            schema_prefs[position] = schemas
    
    return GenreTemplate(
        name=genre.name,
        voices=genre.voices,
        metre=genre.metre,
        texture=genre.texture,
        schema_preferences=schema_prefs,
        cadence_template=genre.cadence_template,
        sections=genre.sections,
        subject_constraints=genre.subject_constraints,
        treatments=genre.treatments,
    )
```

## Planner Integration

```python
# planner/planner.py

def build_plan(brief_path: Path, seed: int | None = None) -> Plan:
    """Build plan from brief file."""
    brief, genre = parse_brief(brief_path)
    
    # Resolve frame (merge brief + genre defaults)
    frame = resolve_frame(brief, genre)
    
    # Schema-first pipeline
    cadence_plan = plan_cadences(frame, genre.cadence_template, genre.sections)
    
    schema_chain = generate_schema_chain(
        cadence_plan=cadence_plan,
        schema_prefs=genre.schema_preferences,
        mode=frame.mode,
        treatments=genre.treatments,
        seed=seed,
    )
    
    # Subject: validate if provided, derive if not
    if brief.subject:
        validation = validate_subject(
            brief.subject,
            schema_chain[0],
            frame.mode,
            genre.subject_constraints,
        )
        assert validation.valid, f"Subject invalid: {validation.errors}"
        subject = brief.subject
    else:
        subject = derive_subject(
            schema_chain[0],
            frame,
            genre.subject_constraints,
        )
    
    # Build structure
    structure = build_structure_from_schemas(schema_chain, cadence_plan)
    
    return Plan(
        brief=brief,
        frame=frame,
        material=Material(subject=subject),
        structure=structure,
        actual_bars=sum(s.bars for s in schema_chain),
    )
```

## Genre File Template

Use this template for all 8 genre files:

```yaml
# data/genres/{genre_name}.yaml
name: {Full Name}
voices: {2|3|4}
metre: {4/4|3/4|etc}
texture: {imitative|melody_bass|homophonic|mixed}

schema_preferences:
  opening:
    - {schema1}
    - {schema2}
  riposte:
    - prinner
  continuation:
    - fonte
    - monte
  pre_cadential:
    - passo_indietro
  cadential:
    - complete_cadence
    - half_cadence

cadence_template:
  density: {high|medium|low}
  first_cadence_bar: {4|8|etc}
  first_cadence_type: {half|authentic}
  section_end_type: {half|authentic}
  final_type: authentic

sections:
  - label: A
    key_area: I
    proportion: {0.0-1.0}
    end_cadence: {half|authentic}
  - label: B
    key_area: {V|I|etc}
    proportion: {0.0-1.0}
    end_cadence: authentic

subject_constraints:
  min_notes: {4}
  max_notes: {12}
  max_bars: {2}
  require_invertible: {true|false}
  require_answerable: {true|false}
  first_degree: [1, 3, 5]
  last_degree: [2, 3, 5, 7]

treatments:
  required: [statement]
  optional: [imitation, sequence, inversion]
  opening: statement
  answer: {imitation|statement}
```

## Migration Checklist

1. [ ] Add new types to `plannertypes.py`
2. [ ] Create `planner/genre_loader.py`
3. [ ] Create `planner/brief_parser.py`
4. [ ] Rewrite `data/genres/invention.yaml`
5. [ ] Rewrite `data/genres/minuet.yaml`
6. [ ] Rewrite `data/genres/gavotte.yaml`
7. [ ] Rewrite `data/genres/sarabande.yaml`
8. [ ] Rewrite `data/genres/bourree.yaml`
9. [ ] Rewrite `data/genres/fantasia.yaml`
10. [ ] Rewrite `data/genres/chorale.yaml`
11. [ ] Rewrite `data/genres/trio_sonata.yaml`
12. [ ] Update `planner/planner.py` to use new modules
13. [ ] Update test briefs to new format
14. [ ] Delete `data/arcs.yaml`
15. [ ] Delete `data/episode_constraints.yaml`
16. [ ] Delete `data/fantasia_arcs.yaml`

## Testing

Convert one brief and run end-to-end:

```bash
# Update freude_invention.brief to new format
# Run planner
python -m planner briefs/builder/freude_invention.brief

# Verify output YAML has:
# - sections with schemas (not episodes)
# - cadence_plan in each section
# - schema slots with type, bars, texture, treatment, voice_entry
```
