"""Audit phrase-boundary intervals for Plan 5.1."""
from pathlib import Path


def analyze(p: Path) -> None:
    rows = []
    with open(p) as f:
        for line in f:
            if line.startswith("#") or line.startswith("offset,"):
                continue
            rows.append(line.strip().split(","))
    soprano = [(float(r[0]), int(r[1]), r[9]) for r in rows if r[3] == "0"]
    bass = [(float(r[0]), int(r[1])) for r in rows if r[3] == "3"]

    # Split soprano into phrases by phrase label
    sop_phrases: list[list[tuple[float, int, str]]] = []
    cur = soprano[0][2]
    grp: list[tuple[float, int, str]] = [soprano[0]]
    for n in soprano[1:]:
        if n[2] != cur:
            sop_phrases.append(grp)
            grp = [n]
            cur = n[2]
        else:
            grp.append(n)
    sop_phrases.append(grp)

    # Find phrase boundary offsets from soprano phrase changes
    boundary_offsets: list[float] = []
    for i in range(1, len(sop_phrases)):
        boundary_offsets.append(sop_phrases[i][0][0])

    # Split bass at the same boundary offsets
    bass_phrases: list[list[tuple[float, int]]] = []
    bi = 0
    for boundary in boundary_offsets:
        phrase_notes = []
        while bi < len(bass) and bass[bi][0] < boundary:
            phrase_notes.append(bass[bi])
            bi += 1
        if phrase_notes:
            bass_phrases.append(phrase_notes)
    # Remaining bass notes
    remaining = []
    while bi < len(bass):
        remaining.append(bass[bi])
        bi += 1
    if remaining:
        bass_phrases.append(remaining)

    print(f"\n=== {p.name} ===")
    print(f"Soprano phrases: {len(sop_phrases)}, Bass phrases: {len(bass_phrases)}")

    # Soprano boundaries
    print(f"\nSoprano boundaries:")
    sop_big = 0
    sop_octave = 0
    sop_total = 0
    for i in range(len(sop_phrases) - 1):
        ex = sop_phrases[i][-1]
        en = sop_phrases[i + 1][0]
        iv = abs(en[1] - ex[1])
        sop_total += iv
        if iv > 7:
            sop_big += 1
        if iv > 12:
            sop_octave += 1
        direction = "up" if en[1] > ex[1] else ("dn" if en[1] < ex[1] else "==")
        print(
            f"  {ex[2]:>12} -> {en[2]:>12} "
            f"| exit={ex[1]:>3} entry={en[1]:>3} interval={iv:>2}st {direction}"
        )
    nb = max(len(sop_phrases) - 1, 1)
    print(f"  >5th(7st): {sop_big}/{nb}, >8ve: {sop_octave}/{nb}, avg: {sop_total / nb:.1f}st")

    # Bass boundaries
    print(f"\nBass boundaries:")
    bass_big = 0
    bass_octave = 0
    bass_total = 0
    for i in range(len(bass_phrases) - 1):
        ex = bass_phrases[i][-1]
        en = bass_phrases[i + 1][0]
        iv = abs(en[1] - ex[1])
        bass_total += iv
        if iv > 7:
            bass_big += 1
        if iv > 12:
            bass_octave += 1
        direction = "up" if en[1] > ex[1] else ("dn" if en[1] < ex[1] else "==")
        print(
            f"  phrase {i:>2} -> {i + 1:>2} "
            f"| exit={ex[1]:>3} entry={en[1]:>3} interval={iv:>2}st {direction}"
        )
    nb_b = max(len(bass_phrases) - 1, 1)
    print(f"  >5th(7st): {bass_big}/{nb_b}, >8ve: {bass_octave}/{nb_b}, avg: {bass_total / nb_b:.1f}st")

    # Simultaneous large leaps
    mn = min(len(sop_phrases), len(bass_phrases))
    simul = 0
    for i in range(mn - 1):
        s_iv = abs(sop_phrases[i + 1][0][1] - sop_phrases[i][-1][1])
        b_iv = abs(bass_phrases[i + 1][0][1] - bass_phrases[i][-1][1])
        if s_iv > 7 and b_iv > 7:
            simul += 1
    print(f"\nSimultaneous large leaps (both >5th): {simul}/{max(mn - 1, 1)}")


if __name__ == "__main__":
    analyze(Path("tests/output/minuet_c_major.note"))
    analyze(Path("tests/output/gavotte_g_major.note"))
