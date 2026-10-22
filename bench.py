#!/usr/bin/env python3
"""Mate-in-N benchmark: 3 famous problems, easiest to hardest.

  .venv/bin/python bench.py --verify                                  # check puzzles with python-chess
  .venv/bin/python bench.py --mock                                    # dry-run with a perfect solver
  .venv/bin/python bench.py --model claude-haiku-5-5 --runs 3         # plain assistant, thinking off
  .venv/bin/python bench.py --model claude-haiku-5-5 --persona grandmaster --thinking
"""
import argparse
import os
import re
import subprocess
import sys

import chess

PUZZLES = [
    {
        "name": "1. Scholar's Mate",
        "mate_in": 1,
        "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
        "solution": "Qxf7#",
    },
    {
        "name": "2. Philidor's Legacy (smothered mate)",
        "mate_in": 2,
        "fen": "5r1k/p5pp/7N/8/8/1Q6/8/6K1 w - - 0 1",
        "solution": "Qg8+ Rxg8 Nf7#",
    },
    {
        "name": "3. Morphy's Opera Game finish",
        "mate_in": 2,
        "fen": "4kb1r/p2n1ppp/4q3/4p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 16",
        "solution": "Qb8+ Nxb8 Rd8#",
    },
]

PERSONAS = {
    "assistant": "You are a helpful assistant.",
    "grandmaster": "You are a chess grandmaster. You read positions carefully and calculate forcing lines precisely.",
}

PROMPT = """You are given a chess position.

FEN: {fen}

Board (White pieces are UPPERCASE, Black pieces are lowercase, "." is an empty square):
{diagram}

Pieces by square:
White: {white}
Black: {black}

{side} to move. Castling rights: {castling}. En passant square: {ep}.
Find a forced checkmate in {n} move{s} (counting only {side}'s moves).

Reply with your reasoning if you like, but the LAST line of your reply must be exactly:
ANSWER: {answer_format}
"""

ANSWER_FORMAT = {
    1: "<the mating move in standard algebraic notation, e.g. Qxf7#>",
    2: "<the full mating line in standard algebraic notation: your move, the opponent's best reply, your mating move, e.g. Qg8+ Rxg8 Nf7#>",
}

ORDER = "KQRBNP"
NAMES = {"K": "King", "Q": "Queen", "R": "Rook", "B": "Bishop", "N": "Knight", "P": "Pawn"}


# ---------- solver ----------

def forces_mate(board, move, n):
    """True if `move` (by the side to move) forces mate within n of its own moves."""
    if move not in board.legal_moves:
        return False
    board.push(move)
    try:
        if board.is_checkmate():
            return True
        if n == 1 or board.is_game_over():
            return False
        for reply in list(board.legal_moves):
            board.push(reply)
            ok = any(forces_mate(board, m, n - 1) for m in list(board.legal_moves))
            board.pop()
            if not ok:
                return False
        return True
    finally:
        board.pop()


def key_moves(board, n):
    return [m for m in list(board.legal_moves) if forces_mate(board, m, n)]


# ---------- prompt ----------

def diagram(board):
    rows = []
    for rank in range(7, -1, -1):
        cells = []
        for file in range(8):
            piece = board.piece_at(chess.square(file, rank))
            cells.append(piece.symbol() if piece else ".")
        rows.append(f"{rank + 1}  " + " ".join(cells))
    rows.append("   a b c d e f g h")
    return "\n".join(rows)


def piece_list(board, color):
    parts = []
    for sym in ORDER:
        squares = sorted(chess.square_name(sq) for sq in board.pieces(chess.Piece.from_symbol(sym).piece_type, color))
        if squares:
            parts.append(f"{NAMES[sym]} {', '.join(squares)}")
    return "; ".join(parts)


def build_prompt(p):
    board = chess.Board(p["fen"])
    side = "White" if board.turn else "Black"
    return PROMPT.format(
        fen=p["fen"],
        diagram=diagram(board),
        white=piece_list(board, chess.WHITE),
        black=piece_list(board, chess.BLACK),
        side=side,
        castling=board.castling_xfen() if board.castling_rights else "none",
        ep=chess.square_name(board.ep_square) if board.ep_square is not None else "none",
        n=p["mate_in"],
        s="" if p["mate_in"] == 1 else "s",
        answer_format=ANSWER_FORMAT[p["mate_in"]],
    )


# ---------- parsing ----------

def extract_answer(reply):
    """Text after the last 'ANSWER:' (markdown stripped), or None."""
    clean = re.sub(r"[*_`]", "", reply)
    hits = re.findall(r"ANSWER\s*:\s*(.*)", clean, flags=re.IGNORECASE)
    return hits[-1].strip() if hits else None


def tokenize(answer):
    answer = re.sub(r"\d+\.(\.\.)?", " ", answer)          # move numbers: 1. 1... 16.
    answer = re.sub(r"[,;()\[\]]|\.\.\.|…", " ", answer)
    return [t.strip(".!?\"'") for t in answer.split() if t.strip(".!?\"'")]


def parse_move(board, text):
    for candidate in (text, text.replace("0", "O").rstrip("+#")):
        for parser in (board.parse_san, board.parse_uci):
            try:
                mv = parser(candidate)
            except ValueError:
                continue
            if "x" in candidate and not board.is_capture(mv):  # python-chess ignores a bogus 'x'
                return None
            return mv
    return None


# ---------- grading ----------

def grade(p, reply):
    """Returns dict: pass, category (pass|no_answer|illegal|wrong), first, line_ok, note."""
    board = chess.Board(p["fen"])
    n = p["mate_in"]
    answer = extract_answer(reply)
    tokens = tokenize(answer) if answer else []
    if not tokens:
        return {"pass": False, "category": "no_answer", "first": None, "line_ok": False, "note": "no ANSWER line"}

    first = parse_move(board, tokens[0])
    if first is None:
        return {"pass": False, "category": "illegal", "first": tokens[0], "line_ok": False,
                "note": f"illegal/unparseable first move {tokens[0]!r}"}
    first_san = board.san(first)
    if not forces_mate(board, first, n):
        return {"pass": False, "category": "wrong", "first": first_san, "line_ok": False,
                "note": f"{first_san} does not force mate in {n}"}

    line_ok, line_note = check_line(board, tokens, n)
    return {"pass": True, "category": "pass", "first": first_san, "line_ok": line_ok,
            "note": first_san + ("" if line_ok else f" (line: {line_note})")}


def check_line(board, tokens, n):
    """The full line must have 2n-1 legal half-moves ending in checkmate."""
    if len(tokens) != 2 * n - 1:
        return False, f"expected {2 * n - 1} moves, got {len(tokens)}"
    b = board.copy()
    for t in tokens:
        mv = parse_move(b, t)
        if mv is None:
            return False, f"illegal move {t!r}"
        b.push(mv)
    return (True, "ok") if b.is_checkmate() else (False, "does not end in checkmate")


# ---------- model runners ----------

def make_claude_cli_asker(model, thinking=False, persona="assistant"):
    env = {k: v for k, v in os.environ.items() if k != "MAX_THINKING_TOKENS"}
    if not thinking:
        env["MAX_THINKING_TOKENS"] = "0"
    cmd = ["claude", "-p", "--model", model, "--tools", "",
           "--strict-mcp-config", "--system-prompt", PERSONAS[persona]]

    def ask(prompt):
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, env=env, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f"claude CLI failed ({r.returncode}): {r.stderr.strip()}")
        return r.stdout

    return ask


def make_mock_asker(puzzles):
    by_prompt = {build_prompt(p): p["solution"] for p in puzzles}
    return lambda prompt: f"ANSWER: {by_prompt[prompt]}"


# ---------- CLI ----------

def verify():
    ok = True
    for p in PUZZLES:
        board = chess.Board(p["fen"])
        n = p["mate_in"]
        keys = key_moves(board, n)
        shorter = key_moves(board, n - 1) if n > 1 else []
        tokens = p["solution"].split()
        line_ok, _ = check_line(board, tokens, n)
        good = len(keys) == 1 and parse_move(board, tokens[0]) == keys[0] and not shorter and line_ok
        ok &= good
        print(f"{'OK ' if good else 'BAD'} {p['name']}: key={[board.san(m) for m in keys]} solution={p['solution']}"
              + (f" (shorter mate exists: {[board.san(m) for m in shorter]})" if shorter else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--persona", choices=PERSONAS, default="assistant")
    ap.add_argument("--thinking", action="store_true", help="leave thinking enabled (default: MAX_THINKING_TOKENS=0)")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--show-reply", action="store_true")
    ap.add_argument("--show-prompt", action="store_true")
    args = ap.parse_args()

    if args.verify:
        sys.exit(0 if verify() else 1)
    if args.show_prompt:
        print(f"SYSTEM: {PERSONAS[args.persona]}\n")
        for p in PUZZLES:
            print("=" * 60, p["name"], "\n" + build_prompt(p))
        return
    if not (args.model or args.mock):
        ap.error("pass --model, --mock, --verify or --show-prompt")

    ask = make_mock_asker(PUZZLES) if args.mock else make_claude_cli_asker(args.model, args.thinking, args.persona)
    total = passed = 0
    print(f"Model: {'mock' if args.mock else args.model}  persona: {args.persona}  "
          f"thinking: {'default' if args.thinking else '0'}  runs/puzzle: {args.runs}\n")
    for p in PUZZLES:
        prompt = build_prompt(p)
        results = []
        for _ in range(args.runs):
            reply = ask(prompt)
            if args.show_reply:
                print(reply, "\n---")
            results.append(grade(p, reply))
        wins = sum(r["pass"] for r in results)
        lines = sum(r["line_ok"] for r in results)
        total += args.runs
        passed += wins
        print(f"{'PASS' if wins == args.runs else 'FAIL'}  {p['name']}  (M{p['mate_in']})  "
              f"{wins}/{args.runs}  line {lines}/{args.runs}  " + "; ".join(r["note"] for r in results))
    print(f"\nScore: {passed}/{total}")


if __name__ == "__main__":
    main()
