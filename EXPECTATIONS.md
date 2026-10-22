# Expectations (written before running)

Hypotheses for each model, with thinking off (`MAX_THINKING_TOKENS=0`, no chain of thought) and with thinking on (default budget).

| Model | Thinking off | Thinking on |
|-------|--------------|-------------|
| Haiku | Fails all 3 | Solves puzzle 1 only |
| Sonnet | Solves puzzle 1 only | Solves all 3 |
| Opus | Solves all 3 | Solves all 3 |

Puzzles: 1 = Scholar's Mate (mate in 1), 2 = Philidor's Legacy (mate in 2), 3 = Morphy's Opera Game finish (mate in 2).

## Reasoning

- **Haiku**: without chain of thought it won't follow the task or apply chess rules reliably: it will misread the board or play illegal moves. With thinking it can find the one-move mate, but not calculate a forced mate in 2.
- **Sonnet**: Scholar's Mate is a well-known pattern it can recognize without thinking. The two mate-in-2 problems need calculation (a queen sacrifice, then checking every reply), so it needs thinking for those.
- **Opus**: strong enough to see both queen-sacrifice mates without explicit thinking. Thinking only adds reliability.

## How a hypothesis is checked

A puzzle counts as **solved** by a model/mode if it passes at least 3 of 5 runs (pass = the first move forces mate, checked by python-chess).
`run_all.py` writes an "Expected vs actual" table at the top of `RESULTS.md` and marks each row confirmed or rejected.
The expectations are also encoded in `EXPECTED` in `run_all.py`. Keep the two in sync.
