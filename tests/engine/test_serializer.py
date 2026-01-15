"""100% coverage tests for engine.serializer.

Tests import only:
- engine.serializer (module under test)
- engine.types (ExpandedPhrase, PieceAST)
- shared (pitch, types)
- stdlib

Serializer module converts ExpandedPhrase lists to YAML.
"""
from fractions import Fraction

import yaml

from shared.pitch import FloatingNote, MidiPitch, Rest
from shared.types import ExpandedVoices, VoiceMaterial

from engine.serializer import (
    InlineList,
    _serialize_phrase,
    _serialize_voice,
    expanded_to_dict,
    fraction_representer,
    inline_list_representer,
    serialize_expanded,
)
from engine.engine_types import (
    EpisodeAST,
    ExpandedPhrase,
    PhraseAST,
    PieceAST,
    SectionAST,
)


def _make_voice_material(voice_index: int, degrees: list[int]) -> VoiceMaterial:
    """Create VoiceMaterial for testing."""
    pitches = [FloatingNote(d) if d > 0 else Rest() for d in degrees]
    durations = [Fraction(1, 4) for _ in degrees]
    return VoiceMaterial(voice_index=voice_index, pitches=pitches, durations=durations)


def _make_expanded_voices(soprano_degrees: list[int], bass_degrees: list[int]) -> ExpandedVoices:
    """Create ExpandedVoices for testing."""
    return ExpandedVoices(voices=[
        _make_voice_material(0, soprano_degrees),
        _make_voice_material(1, bass_degrees),
    ])


def _make_phrase(index: int = 0, bars: int = 2, **kwargs) -> ExpandedPhrase:
    """Create ExpandedPhrase for testing."""
    voices = kwargs.pop("voices", _make_expanded_voices([1, 2, 3], [1, 5, 1]))
    return ExpandedPhrase(
        index=index,
        bars=bars,
        voices=voices,
        cadence=kwargs.pop("cadence", None),
        tonal_target=kwargs.pop("tonal_target", "I"),
        **kwargs,
    )


def _make_piece() -> PieceAST:
    """Create PieceAST for testing."""
    phrase = PhraseAST(
        index=0, bars=2, tonal_target="I", cadence=None, treatment="statement", surprise=None
    )
    episode = EpisodeAST(type="main", bars=2, texture="polyphonic", phrases=(phrase,))
    section = SectionAST(
        label="A", tonal_path=("I",), final_cadence="authentic", episodes=(episode,)
    )
    return PieceAST(
        key="C",
        mode="major",
        metre="4/4",
        tempo="allegro",
        voices=2,
        subject=None,
        sections=(section,),
        arc="imitative",
    )


class TestFractionRepresenter:
    """Test fraction_representer function."""

    def test_zero_fraction(self) -> None:
        """Zero fraction represented as int."""
        dumper = yaml.Dumper("")
        result = fraction_representer(dumper, Fraction(0))
        assert result.value == "0"  # YAML node stores string representation

    def test_non_zero_fraction(self) -> None:
        """Non-zero fraction represented as string."""
        dumper = yaml.Dumper("")
        result = fraction_representer(dumper, Fraction(1, 4))
        assert result.value == "1/4"

    def test_whole_number_fraction(self) -> None:
        """Whole number fraction as string."""
        dumper = yaml.Dumper("")
        result = fraction_representer(dumper, Fraction(2))
        assert result.value == "2"


class TestInlineList:
    """Test InlineList class."""

    def test_is_list(self) -> None:
        """InlineList is a list subclass."""
        il = InlineList([1, 2, 3])
        assert isinstance(il, list)

    def test_contains_items(self) -> None:
        """InlineList contains items."""
        il = InlineList([1, 2, 3])
        assert il == [1, 2, 3]


class TestInlineListRepresenter:
    """Test inline_list_representer function."""

    def test_flow_style(self) -> None:
        """InlineList uses flow style."""
        dumper = yaml.Dumper("")
        data = InlineList([1, 2, 3])
        result = inline_list_representer(dumper, data)
        assert result.flow_style is True


class TestSerializeVoice:
    """Test _serialize_voice function."""

    def test_returns_dict(self) -> None:
        """Returns dictionary."""
        voice = _make_voice_material(0, [1, 2, 3])
        result = _serialize_voice(voice)
        assert isinstance(result, dict)

    def test_has_voice_index(self) -> None:
        """Has voice_index key."""
        voice = _make_voice_material(0, [1, 2, 3])
        result = _serialize_voice(voice)
        assert result["voice_index"] == 0

    def test_has_degrees(self) -> None:
        """Has degrees key."""
        voice = _make_voice_material(0, [1, 2, 3])
        result = _serialize_voice(voice)
        assert result["degrees"] == [1, 2, 3]

    def test_has_durations(self) -> None:
        """Has durations key."""
        voice = _make_voice_material(0, [1, 2, 3])
        result = _serialize_voice(voice)
        assert len(result["durations"]) == 3

    def test_rest_becomes_zero(self) -> None:
        """Rest pitch becomes 0."""
        voice = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), Rest(), FloatingNote(3)],
            durations=[Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)],
        )
        result = _serialize_voice(voice)
        assert result["degrees"] == [1, 0, 3]

    def test_midi_pitch_uses_midi_value(self) -> None:
        """MidiPitch uses midi value."""
        voice = VoiceMaterial(
            voice_index=0,
            pitches=[MidiPitch(60), MidiPitch(64)],
            durations=[Fraction(1, 4), Fraction(1, 4)],
        )
        result = _serialize_voice(voice)
        assert result["degrees"] == [60, 64]

    def test_degrees_inline_list(self) -> None:
        """Degrees is InlineList."""
        voice = _make_voice_material(0, [1, 2])
        result = _serialize_voice(voice)
        assert isinstance(result["degrees"], InlineList)

    def test_durations_inline_list(self) -> None:
        """Durations is InlineList."""
        voice = _make_voice_material(0, [1, 2])
        result = _serialize_voice(voice)
        assert isinstance(result["durations"], InlineList)


class TestSerializePhrase:
    """Test _serialize_phrase function."""

    def test_returns_dict(self) -> None:
        """Returns dictionary."""
        phrase = _make_phrase()
        result = _serialize_phrase(phrase)
        assert isinstance(result, dict)

    def test_has_required_keys(self) -> None:
        """Has required keys."""
        phrase = _make_phrase()
        result = _serialize_phrase(phrase)
        assert "index" in result
        assert "bars" in result
        assert "tonal_target" in result
        assert "voices" in result

    def test_cadence_included_when_present(self) -> None:
        """Cadence included when present."""
        phrase = _make_phrase(cadence="authentic")
        result = _serialize_phrase(phrase)
        assert result["cadence"] == "authentic"

    def test_cadence_excluded_when_none(self) -> None:
        """Cadence excluded when None."""
        phrase = _make_phrase(cadence=None)
        result = _serialize_phrase(phrase)
        assert "cadence" not in result

    def test_is_climax_included_when_true(self) -> None:
        """is_climax included when True."""
        phrase = _make_phrase(is_climax=True)
        result = _serialize_phrase(phrase)
        assert result["is_climax"] is True

    def test_is_climax_excluded_when_false(self) -> None:
        """is_climax excluded when False."""
        phrase = _make_phrase(is_climax=False)
        result = _serialize_phrase(phrase)
        assert "is_climax" not in result

    def test_energy_included_when_present(self) -> None:
        """Energy included when present."""
        phrase = _make_phrase(energy="high")
        result = _serialize_phrase(phrase)
        assert result["energy"] == "high"

    def test_texture_included_when_not_polyphonic(self) -> None:
        """Texture included when not polyphonic."""
        phrase = _make_phrase(texture="homophonic")
        result = _serialize_phrase(phrase)
        assert result["texture"] == "homophonic"

    def test_texture_excluded_when_polyphonic(self) -> None:
        """Texture excluded when polyphonic (default)."""
        phrase = _make_phrase(texture="polyphonic")
        result = _serialize_phrase(phrase)
        assert "texture" not in result

    def test_episode_type_included_when_present(self) -> None:
        """Episode type included when present."""
        phrase = _make_phrase(episode_type="cadenza")
        result = _serialize_phrase(phrase)
        assert result["episode_type"] == "cadenza"

    def test_articulation_included_when_present(self) -> None:
        """Articulation included when present."""
        phrase = _make_phrase(articulation="legato")
        result = _serialize_phrase(phrase)
        assert result["articulation"] == "legato"

    def test_gesture_included_when_present(self) -> None:
        """Gesture included when present."""
        phrase = _make_phrase(gesture="question")
        result = _serialize_phrase(phrase)
        assert result["gesture"] == "question"

    def test_surprise_included_when_present(self) -> None:
        """Surprise included when present."""
        phrase = _make_phrase(surprise="evaded_cadence")
        result = _serialize_phrase(phrase)
        assert result["surprise"] == "evaded_cadence"


class TestExpandedToDict:
    """Test expanded_to_dict function."""

    def test_returns_dict(self) -> None:
        """Returns dictionary."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = expanded_to_dict(piece, phrases)
        assert isinstance(result, dict)

    def test_has_frame(self) -> None:
        """Has frame key."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = expanded_to_dict(piece, phrases)
        assert "frame" in result

    def test_frame_has_key(self) -> None:
        """Frame has key."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = expanded_to_dict(piece, phrases)
        assert result["frame"]["key"] == "C"

    def test_frame_has_mode(self) -> None:
        """Frame has mode."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = expanded_to_dict(piece, phrases)
        assert result["frame"]["mode"] == "major"

    def test_frame_has_metre(self) -> None:
        """Frame has metre."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = expanded_to_dict(piece, phrases)
        assert result["frame"]["metre"] == "4/4"

    def test_frame_has_tempo(self) -> None:
        """Frame has tempo."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = expanded_to_dict(piece, phrases)
        assert result["frame"]["tempo"] == "allegro"

    def test_frame_has_voices(self) -> None:
        """Frame has voices."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = expanded_to_dict(piece, phrases)
        assert result["frame"]["voices"] == 2

    def test_has_phrases(self) -> None:
        """Has phrases key."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = expanded_to_dict(piece, phrases)
        assert "phrases" in result
        assert len(result["phrases"]) == 1

    def test_multiple_phrases(self) -> None:
        """Multiple phrases serialized."""
        piece = _make_piece()
        phrases = [_make_phrase(0), _make_phrase(1)]
        result = expanded_to_dict(piece, phrases)
        assert len(result["phrases"]) == 2


class TestSerializeExpanded:
    """Test serialize_expanded function."""

    def test_returns_string(self) -> None:
        """Returns YAML string."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = serialize_expanded(piece, phrases)
        assert isinstance(result, str)

    def test_valid_yaml(self) -> None:
        """Output is valid YAML."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = serialize_expanded(piece, phrases)
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_contains_frame(self) -> None:
        """Output contains frame."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = serialize_expanded(piece, phrases)
        assert "frame:" in result

    def test_contains_phrases(self) -> None:
        """Output contains phrases."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = serialize_expanded(piece, phrases)
        assert "phrases:" in result

    def test_fractions_as_strings(self) -> None:
        """Fractions represented as strings."""
        piece = _make_piece()
        phrases = [_make_phrase()]
        result = serialize_expanded(piece, phrases)
        # Duration 1/4 should appear as string
        assert "1/4" in result


class TestIntegration:
    """Integration tests for serializer module."""

    def test_roundtrip_parseable(self) -> None:
        """Serialized output is parseable."""
        piece = _make_piece()
        phrases = [
            _make_phrase(0, cadence="authentic", is_climax=True),
            _make_phrase(1, energy="high", texture="homophonic"),
        ]
        result = serialize_expanded(piece, phrases)
        parsed = yaml.safe_load(result)
        assert parsed["frame"]["key"] == "C"
        assert len(parsed["phrases"]) == 2

    def test_rest_handling(self) -> None:
        """Rests serialized as 0."""
        voices = ExpandedVoices(voices=[
            VoiceMaterial(0, [FloatingNote(1), Rest()], [Fraction(1, 4), Fraction(1, 4)]),
            VoiceMaterial(1, [FloatingNote(1), FloatingNote(5)], [Fraction(1, 4), Fraction(1, 4)]),
        ])
        phrase = _make_phrase(voices=voices)
        piece = _make_piece()
        result = serialize_expanded(piece, [phrase])
        parsed = yaml.safe_load(result)
        degrees = parsed["phrases"][0]["voices"][0]["degrees"]
        assert 0 in degrees
