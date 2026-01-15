"""Tests for treatment capability interdictions."""
import pytest

from engine.treatment_caps import (
    allows,
    get_interdictions,
    validate_treatments,
    validate_or_raise,
    KNOWN_CAPABILITIES,
)


class TestGetInterdictions:
    """Tests for get_interdictions function."""

    def test_none_treatment_returns_empty(self):
        """None treatment has no interdictions."""
        assert get_interdictions(None) == frozenset()

    def test_unknown_treatment_returns_empty(self):
        """Unknown treatment defaults to no interdictions."""
        assert get_interdictions("nonexistent_treatment") == frozenset()

    def test_interleaved_is_texture_not_treatment(self):
        """Interleaved is a texture, not a treatment - returns empty interdictions."""
        # interleaved was moved from treatments.yaml to textures.yaml
        # as a texture (voice arrangement) not a treatment (melodic transform)
        interdictions = get_interdictions("interleaved")
        assert interdictions == frozenset()  # Unknown treatments return empty

    def test_statement_forbids_inner_voice(self):
        """Statement treatment forbids inner voice generation."""
        interdictions = get_interdictions("statement")
        assert "inner_voice_gen" in interdictions
        assert "energy_shift" not in interdictions  # Still allows energy

    def test_pedal_tonic_interdictions(self):
        """Pedal treatments forbid inner voice generation."""
        interdictions = get_interdictions("pedal_tonic")
        assert "inner_voice_gen" in interdictions
        assert "energy_shift" not in interdictions


class TestAllows:
    """Tests for allows function."""

    def test_allows_everything_when_no_interdictions(self):
        """Treatments with no interdictions allow all capabilities."""
        # Use 'sequence' which has no interdictions
        for cap in KNOWN_CAPABILITIES:
            assert allows("sequence", cap) is True

    def test_allows_none_treatment(self):
        """None treatment allows everything."""
        for cap in KNOWN_CAPABILITIES:
            assert allows(None, cap) is True

    def test_interleaved_is_texture_allows_all_as_treatment(self):
        """Interleaved as treatment allows everything (it's not a treatment)."""
        # interleaved is now a texture, not a treatment
        # Texture interdictions are checked via texture_allows() in texture.py
        assert allows("interleaved", "energy_shift") is True
        assert allows("interleaved", "climax_boost") is True

    def test_pedal_allows_energy(self):
        """Pedal treatments allow energy shift."""
        assert allows("pedal_tonic", "energy_shift") is True
        assert allows("pedal_dominant", "energy_shift") is True

    def test_pedal_forbids_inner_voice(self):
        """Pedal treatments forbid inner voice generation."""
        assert allows("pedal_tonic", "inner_voice_gen") is False
        assert allows("pedal_dominant", "inner_voice_gen") is False


class TestValidation:
    """Tests for validation functions."""

    def test_validate_treatments_no_errors(self):
        """Current treatments.yaml should have no validation errors."""
        errors = validate_treatments()
        assert errors == []

    def test_validate_or_raise_passes(self):
        """validate_or_raise should not raise with valid config."""
        validate_or_raise()  # Should not raise


class TestTextureInterdictions:
    """Tests for texture capability interdictions."""

    def test_interleaved_texture_has_interdictions(self):
        """Interleaved texture forbids specific capabilities."""
        from engine.texture import texture_allows

        assert not texture_allows("interleaved", "energy_shift")
        assert not texture_allows("interleaved", "climax_boost")
        assert not texture_allows("interleaved", "inner_voice_gen")
        assert not texture_allows("interleaved", "ornaments")
        assert not texture_allows("interleaved", "voice_crossing_penalty")

    def test_polyphonic_texture_allows_all(self):
        """Polyphonic texture has no interdictions."""
        from engine.texture import texture_allows

        assert texture_allows("polyphonic", "energy_shift")
        assert texture_allows("polyphonic", "climax_boost")
        assert texture_allows("polyphonic", "inner_voice_gen")
        assert texture_allows("polyphonic", "ornaments")

    def test_homophonic_texture_forbids_ornaments(self):
        """Homophonic texture forbids ornaments (disrupts synchronization)."""
        from engine.texture import texture_allows

        assert not texture_allows("homophonic", "ornaments")
        assert texture_allows("homophonic", "energy_shift")
