"""Stochastic drift model for humanisation.

Human imprecision modeled as Ornstein-Uhlenbeck process (Brownian motion
with mean reversion) rather than white noise, producing correlated timing
errors that sound natural rather than jittery.
"""
import math
import random

from humanisation.context.types import NoteContext, TimingProfile


class StochasticDrift:
    """Ornstein-Uhlenbeck process for timing drift."""

    def __init__(self, seed: int, sigma: float, theta: float):
        """Initialize drift model.

        Args:
            seed: Random seed for reproducibility
            sigma: Volatility (standard deviation of drift)
            theta: Mean reversion rate (higher = faster return to zero)
        """
        self.rng = random.Random(seed)
        self.sigma = sigma
        self.theta = theta
        self.current = 0.0

    def step(self, dt: float) -> float:
        """Take one O-U step and return current drift.

        The Ornstein-Uhlenbeck process:
        dX = theta * (mu - X) * dt + sigma * dW

        where mu = 0 (mean reversion to zero).

        Args:
            dt: Time step (related to note duration)

        Returns:
            Current drift value in seconds
        """
        # Gaussian noise
        dW = self.rng.gauss(0, 1) * math.sqrt(dt)

        # O-U update
        self.current += self.theta * (0 - self.current) * dt + self.sigma * dW

        # Clamp to reasonable range (max ~30ms drift)
        self.current = max(-0.030, min(0.030, self.current))

        return self.current


def compute_stochastic_offsets(
    contexts: list[NoteContext],
    profile: TimingProfile,
    seed: int,
) -> list[float]:
    """Compute stochastic timing drift for each note.

    Uses Ornstein-Uhlenbeck process so drift is correlated between
    consecutive notes (if you're 10ms late, you're probably still
    ~8ms late on the next note).

    Args:
        contexts: Analysis contexts for each note
        profile: Timing parameters
        seed: Random seed for reproducibility

    Returns:
        List of timing offsets in seconds
    """
    if not contexts:
        return []

    drift = StochasticDrift(
        seed=seed,
        sigma=profile.stochastic_sigma,
        theta=profile.stochastic_theta,
    )

    offsets: list[float] = []
    prev_position = 0.0

    for ctx in contexts:
        # Use phrase position change as proxy for time step
        position = ctx.phrase.position_in_phrase
        dt = max(0.01, abs(position - prev_position))
        prev_position = position

        offset = drift.step(dt)
        offsets.append(offset)

    return offsets
