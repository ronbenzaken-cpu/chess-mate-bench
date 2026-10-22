#!/usr/bin/env python3
"""Grader examples. Run: .venv/bin/python test_grade.py"""
from bench import PUZZLES, grade

SCHOLAR, PHILIDOR, OPERA = PUZZLES

# (puzzle, model reply, expected category, expected line_ok)
CASES = [
    (SCHOLAR, "The queen takes f7 supported by the bishop.\nANSWER: Qxf7#", "pass", True),
    (SCHOLAR, "ANSWER: **Qxf7#**", "pass", True),                          # markdown stripped
    (SCHOLAR, "ANSWER: h5f7", "pass", True),                               # UCI accepted
    (SCHOLAR, "ANSWER: Qxf7", "pass", True),                               # missing '#' tolerated
    (SCHOLAR, "I think Qxf7 wins.", "no_answer", False),                   # no ANSWER line
    (PHILIDOR, "ANSWER: Qg8+ Rxg8 Nf7#", "pass", True),
    (PHILIDOR, "ANSWER: 1. Qg8+ Rxg8 2. Nf7#", "pass", True),              # move numbers ignored
    (PHILIDOR, "ANSWER: Qg8+", "pass", False),                             # right key, no line
    (PHILIDOR, "ANSWER: Qg8+ Kxg8 Nf7#", "pass", False),                   # Kxg8 is illegal (Nh6 guards g8)
    (PHILIDOR, "ANSWER: Nf7+ Rxf7 Qxf7", "wrong", False),                  # legal but not a forced mate
    (PHILIDOR, "ANSWER: No forced mate in 2 found", "gave_up", False),     # model says there is no mate
    (OPERA, "ANSWER: Qb8+ Nxb8 Rd8#", "pass", True),
    (OPERA, "ANSWER: Rd8+ Kxd8 Qb8#", "illegal", False),                   # Rd8 blocked by the knight on d7
    (OPERA, "ANSWER: Bxe7", "illegal", False),                             # no piece to capture on e7
    (OPERA, "first try ANSWER: Rxd7\nactually\nANSWER: Qb8+ Nxb8 Rd8#", "pass", True),  # last ANSWER wins
]

failed = 0
for p, reply, cat, line_ok in CASES:
    g = grade(p, reply)
    ok = g["category"] == cat and g["line_ok"] == line_ok
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {p['name'][:30]:30} {reply.splitlines()[-1][:40]:40} -> {g['category']}, line_ok={g['line_ok']}  {g['note']}")
print(f"\n{len(CASES) - failed}/{len(CASES)} examples graded as expected")
raise SystemExit(1 if failed else 0)
