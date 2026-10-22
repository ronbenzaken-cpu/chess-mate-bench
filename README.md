# chess-mate-bench

Three famous mate-in-N problems, easiest to hardest, for testing whether LLMs find the right move.
Every team runs the same problems so results are comparable.

| # | Problem | Mate in | Key move |
|---|---------|---------|----------|
| 1 | Scholar's Mate | 1 | Qxf7# |
| 2 | Legal's Mate | 1 | Nd5# |
| 3 | Morphy's Opera Game finish | 2 | Qb8+ (Nxb8, Rd8#) |

Each prompt gives the FEN, an ASCII board, and a piece list by square. The model must end with `ANSWER: <move>`.
Grading plays the move on a real board: it must be legal and force mate within the stated number of moves.

## Setup
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Usage
```
.venv/bin/python bench.py --verify                         # confirm each puzzle has a unique key move
.venv/bin/python bench.py --mock                           # dry-run the grader
.venv/bin/python bench.py --model claude-haiku-4-5 --runs 3
```
Models are run via the Claude Code CLI, equivalent to:
```
echo "$PROMPT" | MAX_THINKING_TOKENS=0 claude -p --model <model> --tools "" \
    --strict-mcp-config --system-prompt "You are a helpful assistant."
```
