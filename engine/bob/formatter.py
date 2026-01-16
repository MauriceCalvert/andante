"""Format Bob's report for clipboard output."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Issue:
    """Single diagnostic issue."""
    category: str      # "REFUSES" | "COMPLAINS" | "NOTES"
    bar: int           # 1-indexed
    beat: float        # 1-indexed within bar
    voices: str        # "soprano-bass" | "soprano" | etc.
    message: str       # Bob's perceptual description
    end_bar: int | None = None  # For range issues like "Bars 8-11"


@dataclass
class Report:
    """Complete diagnostic report."""
    issues: list[Issue]

    def to_clipboard(self) -> str:
        """Format for pasting into Claude Code."""
        refuses = [i for i in self.issues if i.category == "REFUSES"]
        complains = [i for i in self.issues if i.category == "COMPLAINS"]
        notes = [i for i in self.issues if i.category == "NOTES"]

        lines: list[str] = ["=== Bob's Report ===", ""]

        if refuses:
            lines.append(f"REFUSES ({len(refuses)}):")
            for issue in refuses:
                lines.append(f"  {_format_issue(issue)}")
            lines.append("")

        if complains:
            lines.append(f"COMPLAINS ({len(complains)}):")
            for issue in complains:
                lines.append(f"  {_format_issue(issue)}")
            lines.append("")

        if notes:
            lines.append(f"NOTES ({len(notes)}):")
            for issue in notes:
                lines.append(f"  {_format_issue(issue)}")
            lines.append("")

        if not (refuses or complains or notes):
            lines.append("No issues found.")
            lines.append("")

        return "\n".join(lines)


def _format_issue(issue: Issue) -> str:
    """Format single issue line."""
    if issue.end_bar is not None:
        loc = f"Bars {issue.bar}-{issue.end_bar}"
    elif issue.beat == 1.0:
        loc = f"Bar {issue.bar} beat 1"
    else:
        loc = f"Bar {issue.bar} beat {issue.beat:.3g}"

    if issue.voices:
        return f"{loc}, {issue.voices}: {issue.message}"
    else:
        return f"{loc}: {issue.message}"


def offset_to_bar_beat(offset: Fraction, bar_duration: Fraction) -> tuple[int, float]:
    """Convert beat offset to 1-indexed bar and beat."""
    bar = int(offset // bar_duration) + 1
    beat_in_bar = float(offset % bar_duration)
    beat = 1.0 + beat_in_bar / float(bar_duration / 4)  # Assumes quarter = 1 beat
    return bar, beat
