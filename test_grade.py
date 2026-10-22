#!/usr/bin/env python3
"""Grader examples. Run: .venv/bin/python test_grade.py"""
from bench import PUZZLES, grade

RETI, IMMORTAL, EVERGREEN = PUZZLES

# (puzzle, model reply, expected category, expected line_ok)
CASES = [
    (RETI, "The bishop gives a double check.\nANSWER: Bg5+ Kc7 Bd8#", "pass", True),
    (RETI, "ANSWER: **Bg5+ Kc7 Bd8#**", "pass", True),                      # markdown stripped
    (RETI, "ANSWER: 1. Bg5+ Kc7 2. Bd8#", "pass", True),                    # move numbers ignored
    (RETI, "ANSWER: Bg5+ Ke8 Rd8#", "pass", True),                          # other defence, also mate
    (RETI, "ANSWER: Bg5+", "pass", False),                                  # right key, no line
    (RETI, "I think Bg5+ wins.", "no_answer", False),                       # no ANSWER line
    (RETI, "ANSWER: Bf4", "wrong", False),                                  # legal but not a forced mate
    (RETI, "ANSWER: Qd8+ Kxd8 Bg5+", "illegal", False),                     # White has no queen
    (RETI, "ANSWER: No forced mate in 2 found", "gave_up", False),          # model says there is no mate
    (IMMORTAL, "ANSWER: Nxg7+ Kd8 Qf6+ Nxf6 Be7#", "pass", True),
    (IMMORTAL, "ANSWER: Nxg7+", "pass", False),                             # right key, no line
    (IMMORTAL, "ANSWER: Nxg7+ Kd8 Qf6+ Nxf6 Bc7#", "pass", False),          # Bc7 is not mate
    (IMMORTAL, "ANSWER: Qf6+ Nxf6 Be7#", "illegal", False),                 # Qf3-f6 blocked by the knight on f5
    (IMMORTAL, "ANSWER: Bc7+", "wrong", False),                             # legal check, no forced mate
    (EVERGREEN, "ANSWER: Qxd7+ Kxd7 Bf5+ Ke8 Bd7+ Kf8 Bxe7#", "pass", True),
    (EVERGREEN, "ANSWER: Qxd7+", "pass", False),                            # right key, no line
    (EVERGREEN, "ANSWER: Rxd7", "illegal", False),                          # Rd1 is blocked by its own bishop on d3
    (EVERGREEN, "ANSWER: Qe4", "wrong", False),                             # legal but not a forced mate
    (EVERGREEN, "first try ANSWER: Qe4\nactually\nANSWER: Qxd7+ Kxd7 Bf5+ Ke8 Bd7+ Kf8 Bxe7#", "pass", True),  # last ANSWER wins
]

failed = 0
for p, reply, cat, line_ok in CASES:
    g = grade(p, reply)
    ok = g["category"] == cat and g["line_ok"] == line_ok
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {p['name'][:30]:30} {reply.splitlines()[-1][:40]:40} -> {g['category']}, line_ok={g['line_ok']}  {g['note']}")
print(f"\n{len(CASES) - failed}/{len(CASES)} examples graded as expected")
raise SystemExit(1 if failed else 0)
