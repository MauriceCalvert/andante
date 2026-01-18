"""Extract domain objects from tree nodes.
Adapters translate Node structures to domain types.
Validation of tree structure happens here, not in domain.
SIZE: 166 lines — Extracts multiple domain types (FrameContext, BarContext,
Subject, Notes) each requiring tree navigation and validation. The functions
are cohesive as they all handle tree-to-domain translation.
Functions:
    extract_frame_context — Root node → FrameContext
    extract_bar_context   — Notes node → BarContext
    extract_subject       — Root node → Subject
    extract_notes         — Subject node → Notes
"""
from fractions import Fraction
from builder.tree import Node
from builder.types import BarContext, FrameContext, Metre, Notes, Subject
from shared.errors import MissingContextError

def extract_frame_context(root: Node) -> FrameContext:
    """Extract frame context from tree root.
    Args:
        root: Tree root node
    Returns:
        FrameContext with key, mode, metre
    Raises:
        MissingContextError: If frame node missing or incomplete
    """
    if "frame" not in root:
        raise MissingContextError("Tree missing 'frame' node")
    frame: Node = root["frame"]
    if "key" not in frame:
        raise MissingContextError("Frame missing 'key'")
    if "mode" not in frame:
        raise MissingContextError("Frame missing 'mode'")
    if "metre" not in frame:
        raise MissingContextError("Frame missing 'metre'")
    metre_str: str = frame["metre"].value
    parts: list[str] = metre_str.split("/")
    metre: Metre = Metre(int(parts[0]), int(parts[1]))
    return FrameContext(
        key=frame["key"].value,
        mode=frame["mode"].value,
        metre=metre,
    )

def extract_bar_context(notes_node: Node) -> BarContext:
    """Extract bar context from a notes node.
    Navigates up the tree to find bar, phrase, and frame context.
    Args:
        notes_node: The 'notes' node in the tree
    Returns:
        BarContext with all needed context
    Raises:
        MissingContextError: If required ancestors missing
    """
    voice: Node | None = notes_node.parent
    if voice is None:
        raise MissingContextError("notes node must have parent voice")
    voices: Node | None = voice.parent
    if voices is None:
        raise MissingContextError("voice node must have parent voices")
    bar: Node | None = voices.parent
    if bar is None:
        raise MissingContextError("voices node must have parent bar")
    role: str = voice["role"].value if "role" in voice else "soprano"
    bar_idx: int = bar["bar_index"].value if "bar_index" in bar else 0
    phrase: Node | None = bar.find_ancestor(
        lambda n: n.parent is not None and n.parent.key == "phrases"
    )
    phrase_treatment: str = "statement"
    phrase_idx: int = 0
    harmony: tuple[str, ...] | None = None
    energy: str = "moderate"
    cadence: str | None = None
    if phrase is not None:
        if "treatment" in phrase:
            phrase_treatment = phrase["treatment"].value
        if "index" in phrase:
            phrase_idx = phrase["index"].value
        if "harmony" in phrase:
            harmony = _extract_harmony(phrase["harmony"])
        if "energy" in phrase:
            energy = phrase["energy"].value
        if "cadence" in phrase and phrase["cadence"].value is not None:
            cadence = phrase["cadence"].value
    frame: FrameContext = extract_frame_context(notes_node.root)
    return BarContext(
        bar_index=bar_idx,
        phrase_index=phrase_idx,
        phrase_treatment=phrase_treatment,
        role=role,
        harmony=harmony,
        frame=frame,
        energy=energy,
        cadence=cadence,
    )

def extract_subject(root: Node) -> Subject | None:
    """Extract subject from material node.
    Args:
        root: Tree root node
    Returns:
        Subject if found, None otherwise
    """
    if "material" not in root or "subject" not in root["material"]:
        return None
    subj: Node = root["material"]["subject"]
    has_pitches: bool = "pitches" in subj
    has_degrees: bool = "degrees" in subj
    if not has_pitches and not has_degrees:
        return None
    notes: Notes = extract_notes(subj)
    source_key: str | None = subj["source_key"].value if "source_key" in subj else None
    return Subject(notes=notes, source_key=source_key, uses_pitches=has_pitches)

def extract_notes(node: Node) -> Notes:
    """Extract Notes from a node with pitches/degrees and durations.
    Args:
        node: Node containing pitches/degrees and durations
    Returns:
        Notes object
    Raises:
        MissingContextError: If required keys missing
    """
    has_pitches: bool = "pitches" in node
    has_degrees: bool = "degrees" in node
    if not has_pitches and not has_degrees:
        raise MissingContextError(f"Node missing 'pitches' or 'degrees' at {node.path_string()}")
    if "durations" not in node:
        raise MissingContextError(f"Node missing 'durations' at {node.path_string()}")
    pitch_key: str = "pitches" if has_pitches else "degrees"
    pitches: list[int] = [c.value for c in node[pitch_key].children]
    durations: list[Fraction] = [Fraction(c.value) for c in node["durations"].children]
    return Notes(tuple(pitches), tuple(durations))

def _extract_harmony(harmony_node: Node) -> tuple[str, ...] | None:
    """Extract harmony tuple from harmony node."""
    if harmony_node.value is None:
        return None
    chords: list[str] = [child.value for child in harmony_node.children]
    return tuple(chords) if chords else None
