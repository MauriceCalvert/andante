"""Subject generator: shape-scored exhaustive generation and selection.

Public API:
- select_subject(): Generate a single subject by seed index
- select_diverse_subjects(): Generate N maximally diverse subjects
- GeneratedSubject: Output dataclass
"""

from motifs.subject_gen.models import GeneratedSubject
from motifs.subject_gen.selector import select_diverse_subjects, select_subject

__all__ = [
    "select_subject",
    "select_diverse_subjects",
    "GeneratedSubject",
]
