"""100% coverage tests for engine.arc_loader.

Tests import only:
- engine.arc_loader (module under test)
- stdlib

Note: We test VoiceTreatmentSpec attributes directly without importing the type.
This avoids coupling to sibling module voice_entry.
"""
from fractions import Fraction

import pytest
from engine.arc_loader import (
    ArcDefinition,
    _ARCS,
    voice_names_for_count,
    load_arc,
    get_arc_voice_count,
    get_default_treatment_for_voice,
)


class TestArcData:
    """Test _ARCS data structure."""

    def test_arcs_loaded(self) -> None:
        assert isinstance(_ARCS, dict)
        assert len(_ARCS) > 0

    def test_imitative_arc_exists(self) -> None:
        assert "imitative" in _ARCS

    def test_fugue_4voice_exists(self) -> None:
        assert "fugue_4voice" in _ARCS


class TestVoiceNamesForCount:
    """Test voice_names_for_count function."""

    def test_2_voices(self) -> None:
        names = voice_names_for_count(2)
        assert names == ("soprano", "bass")

    def test_3_voices(self) -> None:
        names = voice_names_for_count(3)
        assert names == ("soprano", "alto", "bass")

    def test_4_voices(self) -> None:
        names = voice_names_for_count(4)
        assert names == ("soprano", "alto", "tenor", "bass")

    def test_1_voice_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported voice count"):
            voice_names_for_count(1)

    def test_5_voices_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported voice count"):
            voice_names_for_count(5)


class TestArcDefinition:
    """Test ArcDefinition dataclass."""

    def test_frozen(self) -> None:
        arc = load_arc("imitative")
        with pytest.raises(Exception):
            arc.name = "modified"

    def test_has_explicit_entries_false(self) -> None:
        arc = load_arc("imitative")
        assert arc.has_explicit_entries is False

    def test_has_explicit_entries_true(self) -> None:
        arc = load_arc("fugue_4voice")
        assert arc.has_explicit_entries is True


class TestLoadArc:
    """Test load_arc function."""

    def test_imitative_arc(self) -> None:
        arc = load_arc("imitative")
        assert arc.name == "imitative"
        assert arc.voice_count == 2
        assert arc.treatments == ("statement", "imitation", "sequence", "fragmentation", "inversion", "sequence", "imitation", "statement")
        assert arc.climax == "late"
        assert arc.surprise is None
        assert arc.surprise_type is None

    def test_arch_form_arc(self) -> None:
        arc = load_arc("arch_form")
        assert arc.name == "arch_form"
        assert arc.voice_count == 2
        assert arc.surprise is None
        assert arc.surprise_type is None

    def test_fugue_4voice_arc(self) -> None:
        arc = load_arc("fugue_4voice")
        assert arc.name == "fugue_4voice"
        assert arc.voice_count == 4
        assert arc.voice_entries.has_explicit_entries()

    def test_chorale_4voice_no_explicit_entries(self) -> None:
        arc = load_arc("chorale_4voice")
        assert arc.voice_count == 4
        assert arc.has_explicit_entries is False

    def test_dialogue_3voice(self) -> None:
        arc = load_arc("dialogue")
        assert arc.voice_count == 3

    def test_unknown_arc_raises(self) -> None:
        with pytest.raises(AssertionError, match="Unknown arc"):
            load_arc("nonexistent")

    def test_arc_with_empty_treatments(self) -> None:
        arc = load_arc("jubilant")
        assert arc.treatments == ()


class TestGetArcVoiceCount:
    """Test get_arc_voice_count function."""

    def test_2voice_arc(self) -> None:
        assert get_arc_voice_count("imitative") == 2

    def test_3voice_arc(self) -> None:
        assert get_arc_voice_count("dialogue") == 3

    def test_4voice_arc(self) -> None:
        assert get_arc_voice_count("fugue_4voice") == 4

    def test_unknown_arc_raises(self) -> None:
        with pytest.raises(AssertionError, match="Unknown arc"):
            get_arc_voice_count("nonexistent")


class TestGetDefaultTreatmentForVoice:
    """Test get_default_treatment_for_voice function."""

    def test_soprano_outer_voice_2v(self) -> None:
        spec = get_default_treatment_for_voice(0, 0, 2, ("statement", "sequence"))
        assert spec.treatment == "statement"
        assert spec.source == "subject"
        assert spec.interval == 0
        assert spec.delay == Fraction(0)

    def test_bass_outer_voice_2v(self) -> None:
        spec = get_default_treatment_for_voice(0, 1, 2, ("statement", "sequence"))
        assert spec.treatment == "statement"
        assert spec.source == "subject"
        assert spec.interval == -7  # Octave below
        assert spec.delay == Fraction(0)

    def test_soprano_treatment_cycles(self) -> None:
        treatments = ("statement", "sequence", "inversion")
        spec0 = get_default_treatment_for_voice(0, 0, 2, treatments)
        spec1 = get_default_treatment_for_voice(1, 0, 2, treatments)
        spec2 = get_default_treatment_for_voice(2, 0, 2, treatments)
        spec3 = get_default_treatment_for_voice(3, 0, 2, treatments)
        assert spec0.treatment == "statement"
        assert spec1.treatment == "sequence"
        assert spec2.treatment == "inversion"
        assert spec3.treatment == "statement"

    def test_empty_treatments_defaults_to_statement(self) -> None:
        spec = get_default_treatment_for_voice(0, 0, 2, ())
        assert spec.treatment == "statement"

    def test_4voice_alto_phrase0(self) -> None:
        spec = get_default_treatment_for_voice(0, 1, 4, ("statement",))
        assert spec.treatment == "imitation"
        assert spec.source == "subject"
        assert spec.interval == -3
        assert spec.delay == Fraction(1, 2)

    def test_4voice_alto_phrase1_counter_subject(self) -> None:
        spec = get_default_treatment_for_voice(1, 1, 4, ("statement",))
        assert spec.treatment == "imitation"
        assert spec.source == "counter_subject"
        assert spec.interval == 0
        assert spec.delay == Fraction(1, 2)

    def test_4voice_tenor_phrase0_counter_subject(self) -> None:
        spec = get_default_treatment_for_voice(0, 2, 4, ("statement",))
        assert spec.treatment == "imitation"
        assert spec.source == "counter_subject"
        assert spec.interval == -7
        assert spec.delay == Fraction(1)

    def test_4voice_tenor_phrase1_subject(self) -> None:
        spec = get_default_treatment_for_voice(1, 2, 4, ("statement",))
        assert spec.treatment == "imitation"
        assert spec.source == "subject"
        assert spec.interval == -4
        assert spec.delay == Fraction(1)

    def test_4voice_bass_outer(self) -> None:
        spec = get_default_treatment_for_voice(0, 3, 4, ("statement",))
        assert spec.treatment == "statement"
        assert spec.source == "subject"
        assert spec.interval == -7  # Octave below
        assert spec.delay == Fraction(0)

    def test_3voice_alto_phrase0_subject(self) -> None:
        spec = get_default_treatment_for_voice(0, 1, 3, ("statement",))
        assert spec.treatment == "imitation"
        assert spec.source == "subject"
        assert spec.interval == -3
        assert spec.delay == Fraction(1, 2)

    def test_3voice_alto_phrase1_counter_subject(self) -> None:
        spec = get_default_treatment_for_voice(1, 1, 3, ("statement",))
        assert spec.treatment == "imitation"
        assert spec.source == "counter_subject"
        assert spec.interval == 0
        assert spec.delay == Fraction(1, 2)

    def test_3voice_bass_outer(self) -> None:
        spec = get_default_treatment_for_voice(0, 2, 3, ("statement",))
        assert spec.treatment == "statement"
        assert spec.source == "subject"
        assert spec.interval == -7  # Octave below

    def test_unsupported_inner_voice_returns_rest(self) -> None:
        # Call with a hypothetical 5-voice scenario where voice 2 is inner
        # This exercises the fallback rest() return at line 120
        spec = get_default_treatment_for_voice(0, 2, 5, ("statement",))
        assert spec.is_rest
        assert spec.treatment == "rest"

    def test_4voice_inner_voice_3_not_handled(self) -> None:
        # In 4-voice, voice_index 3 is bass (outer), but let's see what happens
        # voice_index 0 is soprano (outer), 1 is alto (handled), 2 is tenor (handled), 3 is bass (outer)
        # So all inner voices in 4-voice are handled. Test passes through 4-voice branch without matching.
        # Actually voice_count=4, voice_index=3: is_outer=True because 3==4-1
        # Need a case where 4-voice inner voice doesn't match 1 or 2
        # That's impossible since inner voices are only 1 and 2 in 4-voice
        pass

    def test_3voice_inner_voice_2_not_handled(self) -> None:
        # In 3-voice: voice 0=soprano (outer), 1=alto (handled at line 115), 2=bass (outer)
        # All cases covered for 3-voice
        pass


class TestFugalConventionCorrectness:
    """Tests challenging the baroque fugal conventions in get_default_treatment_for_voice."""

    def test_alto_interval_is_fourth_not_third(self) -> None:
        """BUG? The docstring says 'subject at 4th below' but code uses interval=-3.

        In baroque fugue, the answer typically enters at the 5th above or 4th below.
        interval=-3 means 3 scale degrees down, which is a 4th (e.g., C to G below).
        Wait - that's actually correct! C(1) down 3 degrees = G(5), a 4th below.

        Actually let me verify: degree 1 - 3 = degree -2, which wraps to degree 5.
        So interval=-3 IS a 4th below. The docstring and code match.
        """
        spec = get_default_treatment_for_voice(0, 1, 4, ("statement",))
        # phrase_index=0, so use_cs=False, source=subject, interval=-3
        assert spec.interval == -3
        # In scale degrees: 1 + (-3) = -2, which wraps to 5 (a 4th below)
        # This is correct for tonal answer in fugue

    def test_tenor_interval_inconsistent_with_docstring(self) -> None:
        """POTENTIAL BUG: Docstring says 'subject at 5th below' but code uses -4.

        The docstring says:
        - Tenor (2): counter_subject, delay 1 bar (or subject at 5th below)

        But for phrase_index=1 (when tenor gets subject):
        interval = -4 (not -5 as docstring suggests)

        Let's verify: degree 1 - 4 = -3, wraps to 4 (a 5th below from 1).
        Wait: 1, 7, 6, 5, 4... that's 4 steps down = 5th below.
        So -4 IS correct for 5th below! The naming is confusing but math works.
        """
        spec = get_default_treatment_for_voice(1, 2, 4, ("statement",))
        # phrase_index=1, so use_cs=False (1%2==0 is False), source=subject
        assert spec.source == "subject"
        assert spec.interval == -4
        # -4 scale degrees from 1: 1->7->6->5->4, which is a 5th below

    def test_counter_subject_interval_should_be_zero(self) -> None:
        """Counter-subject typically doesn't transpose - it moves with the harmony."""
        # When alto gets counter_subject (phrase_index=1)
        spec = get_default_treatment_for_voice(1, 1, 4, ("statement",))
        assert spec.source == "counter_subject"
        assert spec.interval == 0  # Counter-subject not transposed

    def test_bass_gets_subject(self) -> None:
        """Bass states subject like all other voices.

        In baroque fugues, ALL voices state the subject. Bass plays subject
        at octave below.
        """
        for phrase_idx in range(10):
            spec = get_default_treatment_for_voice(phrase_idx, 3, 4, ("statement", "sequence"))
            assert spec.source == "subject"
            assert spec.interval == -7  # Octave below

    def test_staggered_entries_accumulate_delay(self) -> None:
        """Verify that voices enter progressively later.

        In 4-voice fugue exposition:
        - Soprano: delay 0
        - Alto: delay 1/2 bar
        - Tenor: delay 1 bar
        - Bass: delay 0 (subject at octave below)

        This creates the classic fugue texture where voices enter one by one.
        """
        spec_s = get_default_treatment_for_voice(0, 0, 4, ("statement",))
        spec_a = get_default_treatment_for_voice(0, 1, 4, ("statement",))
        spec_t = get_default_treatment_for_voice(0, 2, 4, ("statement",))
        spec_b = get_default_treatment_for_voice(0, 3, 4, ("statement",))

        assert spec_s.delay == Fraction(0)
        assert spec_a.delay == Fraction(1, 2)
        assert spec_t.delay == Fraction(1)
        assert spec_b.delay == Fraction(0)  # Bass enters immediately with subject

    def test_voice_alternation_pattern(self) -> None:
        """Test that alto/tenor alternate between subject and counter-subject.

        phrase 0: alto=subject, tenor=counter_subject
        phrase 1: alto=counter_subject, tenor=subject
        phrase 2: alto=subject, tenor=counter_subject
        ...
        """
        for phrase_idx in range(4):
            alto = get_default_treatment_for_voice(phrase_idx, 1, 4, ("statement",))
            tenor = get_default_treatment_for_voice(phrase_idx, 2, 4, ("statement",))

            if phrase_idx % 2 == 0:
                assert alto.source == "subject", f"phrase {phrase_idx}: alto should have subject"
                assert tenor.source == "counter_subject", f"phrase {phrase_idx}: tenor should have counter_subject"
            else:
                assert alto.source == "counter_subject", f"phrase {phrase_idx}: alto should have counter_subject"
                assert tenor.source == "subject", f"phrase {phrase_idx}: tenor should have subject"
