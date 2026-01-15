"""Voice role system - structural positions independent of SATB naming.

Voices have structural roles, not fixed names. This allows flexible
voice counts while maintaining clear semantics.

Roles:
  TOP     - Highest voice, always track 0
  BOTTOM  - Lowest voice, always track N-1
  INNER_1 - First inner voice (track 1 when voice_count >= 3)
  INNER_2 - Second inner voice (track 2 when voice_count >= 4)

Orchestration mapping (applied later) assigns actual voice names:
  keyboard:  TOP=right_hand, BOTTOM=left_hand
  satb:      TOP=soprano, INNER_1=alto, INNER_2=tenor, BOTTOM=bass
  trio:      TOP=violin, INNER_1=viola, BOTTOM=cello
"""
from enum import Enum
from typing import Sequence


class VoiceRole(Enum):
    """Structural voice roles independent of SATB naming."""
    TOP = "top"          # Highest voice
    INNER_1 = "inner_1"  # First inner voice
    INNER_2 = "inner_2"  # Second inner voice
    BOTTOM = "bottom"    # Lowest voice

    def __str__(self) -> str:
        return self.value


def role_to_track(role: VoiceRole, voice_count: int) -> int:
    """Convert a voice role to track number.

    Track assignment:
      TOP     -> 0
      INNER_1 -> 1 (when voice_count >= 3)
      INNER_2 -> 2 (when voice_count >= 4)
      BOTTOM  -> voice_count - 1
    """
    if role == VoiceRole.TOP:
        return 0
    elif role == VoiceRole.BOTTOM:
        return voice_count - 1
    elif role == VoiceRole.INNER_1:
        if voice_count < 3:
            raise ValueError(f"INNER_1 requires voice_count >= 3, got {voice_count}")
        return 1
    elif role == VoiceRole.INNER_2:
        if voice_count < 4:
            raise ValueError(f"INNER_2 requires voice_count >= 4, got {voice_count}")
        return 2
    else:
        raise ValueError(f"Unknown role: {role}")


def track_to_role(track: int, voice_count: int) -> VoiceRole:
    """Convert a track number to voice role.

    Inverse of role_to_track.
    """
    if track == 0:
        return VoiceRole.TOP
    elif track == voice_count - 1:
        return VoiceRole.BOTTOM
    elif track == 1 and voice_count >= 3:
        return VoiceRole.INNER_1
    elif track == 2 and voice_count >= 4:
        return VoiceRole.INNER_2
    else:
        raise ValueError(f"Invalid track {track} for voice_count {voice_count}")


def get_roles_for_voice_count(voice_count: int) -> tuple[VoiceRole, ...]:
    """Get the ordered list of roles for a given voice count.

    Returns roles in track order (TOP first, BOTTOM last).
    """
    if voice_count == 2:
        return (VoiceRole.TOP, VoiceRole.BOTTOM)
    elif voice_count == 3:
        return (VoiceRole.TOP, VoiceRole.INNER_1, VoiceRole.BOTTOM)
    elif voice_count == 4:
        return (VoiceRole.TOP, VoiceRole.INNER_1, VoiceRole.INNER_2, VoiceRole.BOTTOM)
    else:
        raise ValueError(f"Unsupported voice_count: {voice_count}")


def get_inner_roles(voice_count: int) -> tuple[VoiceRole, ...]:
    """Get only the inner voice roles for a given voice count."""
    if voice_count == 2:
        return ()
    elif voice_count == 3:
        return (VoiceRole.INNER_1,)
    elif voice_count >= 4:
        return (VoiceRole.INNER_1, VoiceRole.INNER_2)
    else:
        raise ValueError(f"Unsupported voice_count: {voice_count}")


# Legacy SATB mapping for backwards compatibility during transition
SATB_TO_ROLE: dict[str, VoiceRole] = {
    "soprano": VoiceRole.TOP,
    "alto": VoiceRole.INNER_1,
    "tenor": VoiceRole.INNER_2,
    "bass": VoiceRole.BOTTOM,
}

ROLE_TO_SATB: dict[VoiceRole, str] = {
    VoiceRole.TOP: "soprano",
    VoiceRole.INNER_1: "alto",
    VoiceRole.INNER_2: "tenor",
    VoiceRole.BOTTOM: "bass",
}


def satb_to_role(satb_name: str) -> VoiceRole:
    """Convert legacy SATB name to role (for backwards compatibility)."""
    if satb_name not in SATB_TO_ROLE:
        raise ValueError(f"Unknown SATB name: {satb_name}")
    return SATB_TO_ROLE[satb_name]


def role_to_satb(role: VoiceRole) -> str:
    """Convert role to legacy SATB name (for backwards compatibility)."""
    return ROLE_TO_SATB[role]
