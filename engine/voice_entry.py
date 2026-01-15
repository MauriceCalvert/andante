"""Voice entry types for N-voice arc-based expansion.

Defines per-phrase voice specifications parsed from arc voice_entries.
Each voice in each phrase gets explicit treatment, source, and interval.
No FILL treatment - every voice needs real material or rest.
"""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class VoiceTreatmentSpec:
    """Treatment specification for one voice in one phrase.

    treatment: The melodic treatment (statement, imitation, sequence, etc.)
               or 'rest' for silent, or 'chordal' for harmonic fill.
    source: Material source ('subject', 'counter_subject').
    interval: Diatonic transposition interval (0 = unison).
    delay: Entry delay in bars (for staggered imitation).
    """
    treatment: str
    source: str | None
    interval: int
    delay: Fraction = Fraction(0)

    @staticmethod
    def rest() -> "VoiceTreatmentSpec":
        """Create a rest specification."""
        return VoiceTreatmentSpec(treatment="rest", source=None, interval=0, delay=Fraction(0))

    @staticmethod
    def from_dict(d: dict) -> "VoiceTreatmentSpec":
        """Parse from YAML dict like {treatment: statement, source: subject}."""
        treatment: str = d.get("treatment", "statement")
        source: str | None = d.get("source")
        interval: int = d.get("interval", 0)
        delay: Fraction = Fraction(d.get("delay", 0))
        return VoiceTreatmentSpec(treatment=treatment, source=source, interval=interval, delay=delay)

    @property
    def is_rest(self) -> bool:
        return self.treatment == "rest"

    @property
    def is_chordal(self) -> bool:
        return self.treatment == "chordal"


@dataclass(frozen=True)
class PhraseVoiceEntry:
    """Voice specifications for all voices in a single phrase.

    phrase_index: Which phrase this applies to.
    texture: 'polyphonic' or 'homophonic'.
    voice_specs: Tuple of VoiceTreatmentSpec, indexed by voice index.
    """
    phrase_index: int
    texture: str
    voice_specs: tuple[VoiceTreatmentSpec, ...]

    def __post_init__(self) -> None:
        assert len(self.voice_specs) >= 2, "Need at least 2 voices"

    @property
    def voice_count(self) -> int:
        return len(self.voice_specs)

    def spec_for_voice(self, index: int) -> VoiceTreatmentSpec:
        assert 0 <= index < len(self.voice_specs), f"Invalid voice index: {index}"
        return self.voice_specs[index]

    @staticmethod
    def from_dict(d: dict, voice_names: tuple[str, ...]) -> "PhraseVoiceEntry":
        """Parse from YAML dict with phrase index and voice specs."""
        phrase_index: int = d["phrase"]
        texture: str = d.get("texture", "polyphonic")
        voices_dict: dict = d.get("voices", {})
        specs: list[VoiceTreatmentSpec] = []
        for name in voice_names:
            if name in voices_dict:
                specs.append(VoiceTreatmentSpec.from_dict(voices_dict[name]))
            else:
                specs.append(VoiceTreatmentSpec.rest())
        return PhraseVoiceEntry(
            phrase_index=phrase_index,
            texture=texture,
            voice_specs=tuple(specs),
        )


@dataclass(frozen=True)
class ArcVoiceEntries:
    """All voice entries for an arc.

    Contains phrase-by-phrase voice specifications.
    If a phrase has no entry, outer voices use arc treatment, inner get default.
    """
    entries: tuple[PhraseVoiceEntry, ...]
    voice_count: int

    def entry_for_phrase(self, phrase_index: int) -> PhraseVoiceEntry | None:
        """Get voice entry for phrase, or None if not specified."""
        for entry in self.entries:
            if entry.phrase_index == phrase_index:
                return entry
        return None

    def has_explicit_entries(self) -> bool:
        return len(self.entries) > 0

    @staticmethod
    def empty(voice_count: int) -> "ArcVoiceEntries":
        """Create empty entries for N voices."""
        return ArcVoiceEntries(entries=(), voice_count=voice_count)

    @staticmethod
    def from_list(
        entries_list: list[dict],
        voice_count: int,
        voice_names: tuple[str, ...],
    ) -> "ArcVoiceEntries":
        """Parse from YAML list of voice entry dicts."""
        entries: list[PhraseVoiceEntry] = []
        for entry_dict in entries_list:
            entries.append(PhraseVoiceEntry.from_dict(entry_dict, voice_names))
        return ArcVoiceEntries(entries=tuple(entries), voice_count=voice_count)
