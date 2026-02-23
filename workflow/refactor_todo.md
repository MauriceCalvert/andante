# Subject Generator Refactoring TODO

## Phase 1: Create Package Structure
- [x] Create motifs/subject_gen/ directory
- [x] Create subject_gen/models.py (GeneratedSubject, _ScoredPitch) - renamed from types.py
- [x] Create subject_gen/constants.py (all configuration constants)
- [x] Create subject_gen/cache.py (disk cache utilities)
- [x] Create subject_gen/validator.py (melodic validity checks)
- [x] Create subject_gen/scoring.py (generic scoring utilities)
- [x] Create subject_gen/contour.py (pitch contour analysis)
- [x] Create subject_gen/pitch_generator.py (Stage 1 pitch generation)
- [x] Create subject_gen/duration_generator.py (Stage 2 duration enumeration)
- [x] Create subject_gen/selector.py (diversity selection)
- [x] Create subject_gen/__init__.py (public API)

## Phase 2: Update Top-Level File
- [x] Reduce subject_generator.py to CLI wrapper (81 lines, was 953)

## Phase 3: Update External Imports
- [x] Update motifs/answer_generator.py (2 imports)
- [x] Update motifs/writers.py (2 imports + X2_TICKS_PER_WHOLE)
- [x] Update motifs/countersubject_generator.py (2 imports)
- [x] Update motifs/stretto_analyser.py (1 import)
- [x] Update motifs/simple_subject.py (partial - file was already broken)

## Phase 4: Verification
- [x] Check cache path compatibility (D:\projects\Barok\barok\source\andante\.cache\subject)
- [x] Verify imports work (all package and external imports successful)
- [x] CLI wrapper works (python -m motifs.subject_generator --help)
- [x] Log to completed.md
