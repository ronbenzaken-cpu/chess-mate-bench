# chess-mate-bench

Three famous checkmate problems, easiest to hardest, for testing whether LLMs find the right moves.
Every team runs the same problems so results are comparable.

| # | Problem | Mate in | Solution |
|---|---------|---------|----------|
| 1 | Scholar's Mate | 1 | Qxf7# |
| 2 | Philidor's Legacy (smothered mate) | 2 | Qg8+ Rxg8 Nf7# |
| 3 | Morphy's Opera Game finish | 2 | Qb8+ Nxb8 Rd8# |

## Setup
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python bench.py --verify     # each puzzle has exactly one winning first move
.venv/bin/python test_grade.py         # grader examples all pass
```

## Test design

3 puzzles x 3 models x 2 thinking modes x 5 runs = **90 calls**.

| Dimension | Values |
|-----------|--------|
| Model | `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5` |
| Thinking | `thinking=0` (`MAX_THINKING_TOKENS=0`) or `thinking=default` (variable unset) |
| Runs | 5 per combination |

Our hypotheses are in [EXPECTATIONS.md](EXPECTATIONS.md).

```
.venv/bin/python run_all.py      # 90 calls -> results.json + RESULTS.md
```

Each model call is equivalent to:
```
echo "$PROMPT" | MAX_THINKING_TOKENS=0 claude -p --model <model> --tools "" \
    --strict-mcp-config --system-prompt "You are a helpful assistant."
```

Single model, quick checks:
```
.venv/bin/python bench.py --show-prompt     # print the exact prompts
.venv/bin/python bench.py --mock            # dry-run the grader
.venv/bin/python bench.py --model claude-haiku-5-5 --thinking --runs 3 --show-reply
```

## The prompt

The board is given three ways so a model can't fail just by misreading the FEN. Example for puzzle 2:

```
You are given a chess position.

FEN: 5r1k/p5pp/7N/8/8/1Q6/8/6K1 w - - 0 1

Board (White pieces are UPPERCASE, Black pieces are lowercase, "." is an empty square):
8  . . . . . r . k
7  p . . . . . p p
6  . . . . . . . N
5  . . . . . . . .
4  . . . . . . . .
3  . Q . . . . . .
2  . . . . . . . .
1  . . . . . . K .
   a b c d e f g h

Pieces by square:
White: King g1; Queen b3; Knight h6
Black: King h8; Rook f8; Pawn a7, g7, h7

White to move. Castling rights: none. En passant square: none.
Find a forced checkmate in 2 moves (counting only White's moves).

Reply with your reasoning if you like, but the LAST line of your reply must be exactly:
ANSWER: <the full mating line in standard algebraic notation: your move, the opponent's best reply, your mating move, e.g. Qg8+ Rxg8 Nf7#>
```

## Parsing and grading

1. Take the text after the **last** `ANSWER:` and strip markdown (`**`, `` ` ``, `_`).
2. Drop move numbers (`1.`, `1...`) and split into moves. SAN or UCI is accepted, and a missing `+` or `#` is tolerated. A capture `x` on a square with no piece is rejected.
3. **Pass** = the first move is legal **and** forces mate in N against every defence (checked by python-chess, not by matching text).
4. **Line correct** (secondary score) = the whole line is legal, has 2N-1 moves and ends in checkmate.

Every failure falls into one category:

| Category | Meaning |
|----------|---------|
| `no_answer` | No `ANSWER:` line |
| `illegal` | First move is illegal or unparseable: the model misread the board |
| `wrong` | First move is legal but doesn't force mate: the model miscalculated |
| `error` | CLI call failed |

### Example replies (from `test_grade.py`)

| Puzzle | Reply's last line | Result | Line correct |
|--------|-------------------|--------|--------------|
| 1 | `ANSWER: Qxf7#` | pass | yes |
| 1 | `ANSWER: **Qxf7#**` | pass | yes |
| 1 | `ANSWER: h5f7` (UCI) | pass | yes |
| 1 | `I think Qxf7 wins.` | no_answer | no |
| 2 | `ANSWER: 1. Qg8+ Rxg8 2. Nf7#` | pass | yes |
| 2 | `ANSWER: Qg8+` | pass | no (line missing) |
| 2 | `ANSWER: Qg8+ Kxg8 Nf7#` | pass | no (Kxg8 illegal, Nh6 guards g8) |
| 2 | `ANSWER: Nf7+ Rxf7 Qxf7` | wrong | no |
| 3 | `ANSWER: Rd8+ Kxd8 Qb8#` | illegal | no (d7 knight blocks the rook) |
| 3 | `ANSWER: Bxe7` | illegal | no (nothing to capture on e7) |

## Output

`run_all.py` writes `results.json` (every reply, raw) and `RESULTS.md` with:
- expected vs actual per model x thinking mode (a puzzle is "solved" at 3/5 or more passes)
- pass rate per puzzle for each model x thinking mode
- full-line-correct rate
- failure-category counts and a list of every failure
