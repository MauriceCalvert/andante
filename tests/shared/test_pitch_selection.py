"""Tests for shared/pitch_selection.py — constraint-relaxation pitch selection."""
from fractions import Fraction

from builder.types import Note
from builder.voice_types import VoiceConfig, VoiceContext
from shared.key import Key
from shared.pitch_selection import select_best_pitch


def _note(offset: Fraction, pitch: int, voice: int = 0) -> Note:
    return Note(offset=offset, pitch=pitch, duration=Fraction(1, 4), voice=voice)


def _config(voice_id: int = 0) -> VoiceConfig:
    return VoiceConfig(
        voice_id=voice_id,
        range_low=55,
        range_high=84,
        key=Key(tonic="C", mode="major"),
        metre="4/4",
        bar_length=Fraction(1),
        beat_unit=Fraction(1, 4),
        phrase_start=Fraction(0),
        genre="invention",
        character="plain",
        is_minor=False,
        guard_tolerance=frozenset(),
        cadence_type=None,
    )


def _context(
    other_voices: dict[int, tuple[Note, ...]] | None = None,
    own_prior: tuple[Note, ...] = (),
    prior_tail: Note | None = None,
    structural: frozenset[Fraction] = frozenset(),
) -> VoiceContext:
    return VoiceContext(
        other_voices=other_voices if other_voices is not None else {},
        own_prior_notes=own_prior,
        prior_phrase_tail=prior_tail,
        structural_offsets=structural,
    )


class TestSelectBestPitch:
    def test_single_candidate_returns_it(self) -> None:
        result: int = select_best_pitch(
            candidates=(60,),
            offset=Fraction(0),
            config=_config(),
            context=_context(),
            own_previous=(),
        )
        assert result == 60

    def test_prefers_no_voice_crossing(self) -> None:
        """With bass voice below, prefer pitch that doesn't cross."""
        bass_note: Note = _note(Fraction(1, 4), 62, voice=3)
        cfg: VoiceConfig = _config(voice_id=0)  # soprano
        ctx: VoiceContext = _context(
            other_voices={3: (bass_note,)},
        )
        # 58 crosses below bass 62; 65 does not
        result: int = select_best_pitch(
            candidates=(58, 65),
            offset=Fraction(1, 4),
            config=cfg,
            context=ctx,
            own_previous=(),
        )
        assert result == 65

    def test_prefers_no_parallel_fifths(self) -> None:
        """Avoid parallel perfect fifths."""
        # Previous: soprano 67 (G4) over bass 60 (C4) = P5
        # Bass moves to D4=62. Soprano to A4=69 would be P5 again.
        bass_notes: tuple[Note, ...] = (
            _note(Fraction(0), 60, voice=3),
            _note(Fraction(1, 4), 62, voice=3),
        )
        prev_soprano: Note = _note(Fraction(0), 67, voice=0)
        cfg: VoiceConfig = _config(voice_id=0)
        ctx: VoiceContext = _context(
            other_voices={3: bass_notes},
        )
        # 69 creates parallel P5; 65 (F4) does not
        result: int = select_best_pitch(
            candidates=(69, 65),
            offset=Fraction(1, 4),
            config=cfg,
            context=ctx,
            own_previous=(prev_soprano,),
        )
        assert result == 65

    def test_prefers_step_recovery_after_leap(self) -> None:
        """After a leap, prefer contrary step."""
        prev_notes: tuple[Note, ...] = (
            _note(Fraction(0), 60),       # C4
            _note(Fraction(1, 4), 67),    # G4 (leap up)
        )
        cfg: VoiceConfig = _config()
        ctx: VoiceContext = _context()
        # 65 = F4 (step down, recovery); 72 = C5 (leap up, no recovery)
        result: int = select_best_pitch(
            candidates=(72, 65),
            offset=Fraction(1, 2),
            config=cfg,
            context=ctx,
            own_previous=prev_notes,
        )
        assert result == 65

    def test_all_candidates_evaluated(self) -> None:
        """Verifies that even with identical penalties, a result is returned."""
        result: int = select_best_pitch(
            candidates=(60, 62, 64),
            offset=Fraction(0),
            config=_config(),
            context=_context(),
            own_previous=(),
        )
        assert result in (60, 62, 64)

    def test_avoids_ugly_interval(self) -> None:
        """Prefer non-ugly interval over ugly one."""
        prev: Note = _note(Fraction(0), 60)
        cfg: VoiceConfig = _config()
        ctx: VoiceContext = _context()
        # 66 = F#4 (tritone from C4, ugly); 64 = E4 (M3, fine)
        result: int = select_best_pitch(
            candidates=(66, 64),
            offset=Fraction(1, 4),
            config=cfg,
            context=ctx,
            own_previous=(prev,),
        )
        assert result == 64

    def test_avoids_cross_bar_repetition(self) -> None:
        """Prefer different pitch across bar boundary."""
        prev: Note = _note(Fraction(3, 4), 67)  # end of bar 1
        cfg: VoiceConfig = _config()
        ctx: VoiceContext = _context()
        # 67 = same pitch across bar (bad); 65 = different (fine)
        result: int = select_best_pitch(
            candidates=(67, 65),
            offset=Fraction(1),  # start of bar 2
            config=cfg,
            context=ctx,
            own_previous=(prev,),
        )
        assert result == 65
