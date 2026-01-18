"""Rigid YAML validation: catch all errors at parse time."""
from fractions import Fraction
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"

# Load all vocabularies once at import
_TREATMENTS_DATA: dict = yaml.safe_load(open(DATA_DIR / "treatments.yaml"))
TREATMENTS: set[str] = set(_TREATMENTS_DATA.keys())
RHYTHMS: set[str] = set(yaml.safe_load(open(DATA_DIR / "rhythms.yaml")).keys())
ARCS: set[str] = set(yaml.safe_load(open(DATA_DIR / "arcs.yaml")).keys())
GESTURES: set[str] = set(yaml.safe_load(open(DATA_DIR / "gestures.yaml")).keys())
DEVICES: set[str] = set(yaml.safe_load(open(DATA_DIR / "devices.yaml")).keys())
EPISODES: set[str] = set(yaml.safe_load(open(DATA_DIR / "episodes.yaml")).keys())
ENERGY_LEVELS: set[str] = set(yaml.safe_load(open(DATA_DIR / "energy.yaml"))["levels"].keys())
SURPRISES: set[str] = set(yaml.safe_load(open(DATA_DIR / "surprises.yaml"))["types"].keys())
_cad = yaml.safe_load(open(DATA_DIR / "cadences.yaml"))
CADENCES: set[str] = {k for k, v in _cad.items() if "top" in v and "approach" not in v}

# Valid values
VALID_KEYS: set[str] = {"C", "D", "E", "F", "G", "A", "B",
                        "C#", "D#", "F#", "G#", "A#",
                        "Db", "Eb", "Gb", "Ab", "Bb"}
VALID_MODES: set[str] = {"major", "minor"}
VALID_TEMPOS: set[str] = {"largo", "adagio", "andante", "moderato", "allegro", "vivace", "presto"}
VALID_FORMS: set[str] = {"through_composed", "binary", "rounded_binary", "ternary"}
VALID_TONAL_TARGETS: set[str] = {"I", "II", "III", "IV", "V", "VI", "VII",
                                  "i", "ii", "iii", "iv", "v", "vi", "vii"}
VALID_SECTION_CADENCES: set[str] = {"authentic", "half", "deceptive", "plagal", "phrygian"}

# Fields that belong in frame, not brief
FRAME_FIELDS: set[str] = {"key", "mode", "metre", "tempo", "voices", "upbeat", "form"}


class ValidationError(Exception):
    """Raised when YAML validation fails."""
    pass


def _err(context: str, msg: str) -> ValidationError:
    """Create validation error with context."""
    return ValidationError(f"{context}: {msg}")


def validate_frame(frame: dict) -> None:
    """Validate frame section."""
    ctx: str = "frame"
    assert "key" in frame, _err(ctx, "missing 'key'")
    assert frame["key"] in VALID_KEYS, _err(ctx, f"invalid key '{frame['key']}', must be one of {VALID_KEYS}")
    assert "mode" in frame, _err(ctx, "missing 'mode'")
    assert frame["mode"] in VALID_MODES, _err(ctx, f"invalid mode '{frame['mode']}', must be major or minor")
    assert "metre" in frame, _err(ctx, "missing 'metre'")
    metre: str = frame["metre"]
    assert "/" in metre, _err(ctx, f"metre '{metre}' must be in format N/D (e.g. 4/4)")
    num, den = metre.split("/")
    assert num.isdigit() and den.isdigit(), _err(ctx, f"metre '{metre}' must have numeric values")
    assert int(den) in {2, 4, 8, 16}, _err(ctx, f"metre denominator must be 2, 4, 8, or 16")
    assert "tempo" in frame, _err(ctx, "missing 'tempo'")
    assert frame["tempo"] in VALID_TEMPOS, _err(ctx, f"invalid tempo '{frame['tempo']}', must be one of {VALID_TEMPOS}")
    assert "voices" in frame, _err(ctx, "missing 'voices'")
    assert frame["voices"] in {2, 3, 4}, _err(ctx, f"voices must be 2, 3, or 4, got {frame['voices']}")
    if "form" in frame:
        assert frame["form"] in VALID_FORMS, _err(ctx, f"invalid form '{frame['form']}', must be one of {VALID_FORMS}")
    if "upbeat" in frame:
        upbeat = frame["upbeat"]
        if upbeat != 0:
            assert "/" in str(upbeat), _err(ctx, f"upbeat '{upbeat}' must be fraction or 0")


def validate_subject(subject: dict, metre: str) -> None:
    """Validate subject/motif."""
    ctx: str = "material.subject"
    assert "degrees" in subject, _err(ctx, "missing 'degrees'")
    assert "durations" in subject, _err(ctx, "missing 'durations'")
    assert "bars" in subject, _err(ctx, "missing 'bars'")
    degrees: list = subject["degrees"]
    durations: list = subject["durations"]
    bars: int = subject["bars"]
    assert len(degrees) == len(durations), _err(ctx, f"degrees ({len(degrees)}) and durations ({len(durations)}) must have same length")
    assert len(degrees) >= 2, _err(ctx, "subject must have at least 2 notes")
    assert bars >= 1, _err(ctx, f"bars must be >= 1, got {bars}")
    for i, d in enumerate(degrees):
        assert isinstance(d, int) and 1 <= d <= 7, _err(ctx, f"degree[{i}] = {d} must be int 1-7")
    dur_sum: Fraction = Fraction(0)
    for i, d in enumerate(durations):
        dur_str: str = str(d)
        if "/" in dur_str:
            num, den = dur_str.split("/")
            dur_sum += Fraction(int(num), int(den))
        else:
            dur_sum += Fraction(int(d))
    num_str, den_str = metre.split("/")
    bar_dur: Fraction = Fraction(int(num_str), int(den_str))
    expected: Fraction = bar_dur * bars
    assert dur_sum == expected, _err(ctx, f"durations sum to {dur_sum}, expected {expected} for {bars} bar(s) in {metre}")


def validate_phrase(phrase: dict, phrase_idx: int, section_label: str, episode_idx: int) -> None:
    """Validate a single phrase."""
    ctx: str = f"section[{section_label}].episode[{episode_idx}].phrase[{phrase_idx}]"
    assert "index" in phrase, _err(ctx, "missing 'index'")
    assert phrase["index"] == phrase_idx, _err(ctx, f"index mismatch: expected {phrase_idx}, got {phrase['index']}")
    assert "bars" in phrase, _err(ctx, "missing 'bars'")
    assert phrase["bars"] >= 1, _err(ctx, f"bars must be >= 1, got {phrase['bars']}")
    assert "tonal_target" in phrase, _err(ctx, "missing 'tonal_target'")
    target: str = phrase["tonal_target"]
    assert target in VALID_TONAL_TARGETS, _err(ctx, f"invalid tonal_target '{target}', must be one of {VALID_TONAL_TARGETS}")
    assert "treatment" in phrase, _err(ctx, "missing 'treatment'")
    treatment: str = phrase["treatment"]
    # Strip figurae annotations like "statement[fuga+lombardic]" -> "statement"
    base_treatment: str = treatment.split("[")[0] if "[" in treatment else treatment
    assert base_treatment in TREATMENTS, _err(ctx, f"invalid treatment '{base_treatment}', must be one of {TREATMENTS}")
    cadence = phrase.get("cadence")
    if cadence is not None:
        assert cadence in CADENCES, _err(ctx, f"invalid cadence '{cadence}', must be one of {CADENCES}")
    rhythm = phrase.get("rhythm")
    if rhythm is not None:
        assert rhythm in RHYTHMS, _err(ctx, f"invalid rhythm '{rhythm}', must be one of {RHYTHMS}")
    gesture = phrase.get("gesture")
    if gesture is not None:
        assert gesture in GESTURES, _err(ctx, f"invalid gesture '{gesture}', must be one of {GESTURES}")
    device = phrase.get("device")
    if device is not None:
        assert device in DEVICES, _err(ctx, f"invalid device '{device}', must be one of {DEVICES}")
    energy = phrase.get("energy")
    if energy is not None:
        assert energy in ENERGY_LEVELS, _err(ctx, f"invalid energy '{energy}', must be one of {ENERGY_LEVELS}")
    surprise = phrase.get("surprise")
    if surprise is not None:
        assert surprise in SURPRISES, _err(ctx, f"invalid surprise '{surprise}', must be one of {SURPRISES}")


def validate_episode(episode: dict, episode_idx: int, section_label: str, global_phrase_idx: int, tonal_path: list) -> int:
    """Validate an episode. Returns next global phrase index."""
    ctx: str = f"section[{section_label}].episode[{episode_idx}]"
    assert "type" in episode, _err(ctx, "missing 'type'")
    ep_type: str = episode["type"]
    assert ep_type in EPISODES, _err(ctx, f"invalid episode type '{ep_type}', must be one of {EPISODES}")
    assert "bars" in episode, _err(ctx, "missing 'bars'")
    assert episode["bars"] >= 1, _err(ctx, f"bars must be >= 1, got {episode['bars']}")
    assert "phrases" in episode, _err(ctx, "missing 'phrases'")
    phrases: list = episode["phrases"]
    assert len(phrases) >= 1, _err(ctx, "must have at least 1 phrase")
    for i, phrase in enumerate(phrases):
        validate_phrase(phrase, global_phrase_idx + i, section_label, episode_idx)
        target: str = phrase["tonal_target"]
        assert target in tonal_path, _err(f"{ctx}.phrase[{i}]", f"tonal_target '{target}' not in section tonal_path {tonal_path}")
    return global_phrase_idx + len(phrases)


def validate_section(section: dict, section_idx: int, global_phrase_idx: int) -> int:
    """Validate a section. Returns next global phrase index."""
    ctx: str = f"section[{section_idx}]"
    assert "label" in section, _err(ctx, "missing 'label'")
    label: str = section["label"]
    assert "tonal_path" in section, _err(ctx, "missing 'tonal_path'")
    tonal_path: list = section["tonal_path"]
    assert len(tonal_path) >= 1, _err(ctx, "tonal_path must have at least 1 target")
    for i, target in enumerate(tonal_path):
        assert target in VALID_TONAL_TARGETS, _err(ctx, f"tonal_path[{i}] '{target}' invalid")
    assert "final_cadence" in section, _err(ctx, "missing 'final_cadence'")
    fc: str = section["final_cadence"]
    assert fc in VALID_SECTION_CADENCES, _err(ctx, f"invalid final_cadence '{fc}'")
    assert "episodes" in section, _err(ctx, "missing 'episodes'")
    episodes: list = section["episodes"]
    assert len(episodes) >= 1, _err(ctx, "must have at least 1 episode")
    for i, episode in enumerate(episodes):
        global_phrase_idx = validate_episode(episode, i, label, global_phrase_idx, tonal_path)
    return global_phrase_idx


def validate_structure(structure: dict) -> None:
    """Validate structure section."""
    ctx: str = "structure"
    assert "arc" in structure, _err(ctx, "missing 'arc'")
    arc: str = structure["arc"]
    assert arc in ARCS, _err(ctx, f"invalid arc '{arc}', must be one of {ARCS}")
    assert "sections" in structure, _err(ctx, "missing 'sections'")
    sections: list = structure["sections"]
    assert len(sections) >= 1, _err(ctx, "must have at least 1 section")
    phrase_idx: int = 0
    for i, section in enumerate(sections):
        phrase_idx = validate_section(section, i, phrase_idx)
    all_phrases: list = [p for s in sections for e in s["episodes"] for p in e["phrases"]]
    final_phrase: dict = all_phrases[-1]
    assert final_phrase.get("cadence") == "authentic", _err("structure", "final phrase must have authentic cadence")
    assert final_phrase["bars"] >= 2, _err("structure", f"final phrase needs >= 2 bars for authentic cadence, got {final_phrase['bars']}")
    # Opening phrase must use soprano_direct treatment to present subject clearly
    opening_phrase: dict = all_phrases[0]
    opening_treatment: str = opening_phrase["treatment"].split("[")[0]
    treatment_config: dict = _TREATMENTS_DATA.get(opening_treatment, {})
    has_soprano_direct: bool = treatment_config.get("soprano_direct", False)
    assert has_soprano_direct, _err(
        "structure.phrase[0]",
        f"opening phrase treatment '{opening_treatment}' must have soprano_direct=true to present subject clearly"
    )


def validate_yaml(data: dict) -> None:
    """Validate complete YAML structure. Raises ValidationError on failure."""
    assert "frame" in data, _err("root", "missing 'frame' section")
    assert "material" in data, _err("root", "missing 'material' section")
    assert "structure" in data, _err("root", "missing 'structure' section")
    validate_frame(data["frame"])
    validate_material(data["material"], data["frame"]["metre"])
    validate_structure(data["structure"])


def validate_file(path: Path) -> None:
    """Validate a YAML file. Raises ValidationError on failure."""
    with open(path, encoding="utf-8") as f:
        content: str = f.read()
    # YAML doesn't allow tabs for indentation - convert to spaces
    content = content.replace("\t", "  ")
    data: dict = yaml.safe_load(content)
    validate_yaml(data)


def validate_brief_yaml(data: dict) -> None:
    """Validate brief YAML structure before parsing.

    Checks:
    1. 'brief:' section must exist at root
    2. Frame fields must not appear under brief
    3. Either brief.bars XOR structure with fully specified bars (not both, not neither)
    """
    # Rule 1: brief section required
    if "brief" not in data:
        raise ValidationError(
            "root: missing 'brief:' section. The file must start with 'brief:' header."
        )

    brief_data: dict = data.get("brief", {})

    # Rule 2: Frame fields must not be under brief
    misplaced: list[str] = [f for f in FRAME_FIELDS if f in brief_data]
    if misplaced:
        raise ValidationError(
            f"Frame fields found under 'brief:' section: {misplaced}. "
            f"These belong under 'frame:' section. Add 'frame:' before {misplaced[0]}:"
        )

    # Rule 3: bars in brief XOR fully specified in structure
    has_brief_bars: bool = "bars" in brief_data
    has_structure: bool = "structure" in data

    if has_structure:
        # Check if structure has all bars specified
        structure: dict = data["structure"]
        sections: list = structure.get("sections", [])
        structure_bars_specified: bool = _structure_has_all_bars(sections)

        if has_brief_bars and structure_bars_specified:
            raise ValidationError(
                "brief.bars and structure bars are mutually exclusive. "
                "Either specify bars in brief (planner allocates) OR specify bars on all phrases in structure, not both."
            )
        if not has_brief_bars and not structure_bars_specified:
            raise ValidationError(
                "Must specify bars either in brief.bars OR on all phrases in structure. "
                "Neither was found."
            )
    else:
        # No structure means we need brief.bars for planner
        if not has_brief_bars:
            raise ValidationError(
                "brief: missing 'bars'. When structure is not provided, brief.bars is required."
            )


def _structure_has_all_bars(sections: list) -> bool:
    """Check if all phrases in structure have explicit bars."""
    if not sections:
        return False
    for section in sections:
        for episode in section.get("episodes", []):
            for phrase in episode.get("phrases", []):
                if "bars" not in phrase:
                    return False
    return True


def validate_material(material: dict, metre: str) -> None:
    """Validate material section with file reference support.

    Subject can be inline (degrees/durations/bars) or from file.
    If subject is from file, counter_subject must also be from file or omitted.
    """
    ctx: str = "material"
    if "subject" not in material:
        raise _err(ctx, "missing 'subject'")

    subject: dict = material["subject"]
    subject_from_file: bool = "file" in subject

    # Validate subject
    if subject_from_file:
        _validate_file_reference(subject, f"{ctx}.subject")
    else:
        validate_subject(subject, metre)

    # Validate counter_subject if present
    if "counter_subject" in material:
        cs: dict = material["counter_subject"]
        cs_from_file: bool = "file" in cs

        if subject_from_file and not cs_from_file:
            raise ValidationError(
                f"{ctx}: when subject uses 'file:', counter_subject must also use 'file:' or be omitted"
            )

        if cs_from_file:
            _validate_file_reference(cs, f"{ctx}.counter_subject")
        else:
            _validate_counter_subject(cs, metre)


def _validate_file_reference(motif: dict, ctx: str) -> None:
    """Validate a motif that uses file reference."""
    inline_fields: set[str] = {"degrees", "durations", "bars"}
    conflicting: list[str] = [f for f in inline_fields if f in motif]
    if conflicting:
        raise ValidationError(
            f"{ctx}: 'file:' is mutually exclusive with {conflicting}. "
            f"Use either file reference OR inline degrees/durations/bars, not both."
        )
    file_path: str = motif.get("file", "")
    if not file_path:
        raise ValidationError(f"{ctx}: 'file:' cannot be empty")


def _validate_counter_subject(cs: dict, metre: str) -> None:
    """Validate inline counter_subject."""
    ctx: str = "material.counter_subject"
    if "degrees" not in cs:
        raise _err(ctx, "missing 'degrees'")
    if "durations" not in cs:
        raise _err(ctx, "missing 'durations'")
    if "bars" not in cs:
        raise _err(ctx, "missing 'bars'")
    degrees: list = cs["degrees"]
    durations: list = cs["durations"]
    bars: int = cs["bars"]
    if len(degrees) != len(durations):
        raise _err(ctx, f"degrees ({len(degrees)}) and durations ({len(durations)}) must have same length")
    if len(degrees) < 2:
        raise _err(ctx, "counter_subject must have at least 2 notes")
    if bars < 1:
        raise _err(ctx, f"bars must be >= 1, got {bars}")
