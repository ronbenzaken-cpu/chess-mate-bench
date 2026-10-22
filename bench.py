#!/usr/bin/env python3
"""Mate-in-N benchmark: 3 famous problems, easiest to hardest.

  .venv/bin/python bench.py --verify                      # check puzzles with python-chess
  .venv/bin/python bench.py --model claude-haiku-4-5       # test a model (runs `claude -p`, no thinking, no tools)
  .venv/bin/python bench.py --model claude-haiku-5-5 --runs 3
  .venv/bin/python bench.py --mock                        # dry-run with a perfect solver
"""
import argparse
import re
import sys

import chess

PUZZLES = [
    {
        "name": "1. Scholar's Mate",
        "mate_in": 1,
        "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
        "key": "Qxf7#",
    },
    {
        "name": "2. Legal's Mate",
        "mate_in": 1,
        "fen": "rn1q1bnr/ppp1kB1p/3p2p1/4N3/4P3/2N5/PPPP1PPP/R1BbK2R w KQ - 1 7",
        "key": "Nd5#",
    },
    {
        "name": "3. Morphy's Opera Game finish",
        "mate_in": 2,
        "fen": "4kb1r/p2n1ppp/4q3/4p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 16",
        "key": "Qb8+",
    },
]


def mating_moves(board):
    out = []
    for mv in list(board.legal_moves):
        board.push(mv)
        if board.is_checkmate():
            out.append(mv)
        board.pop()
    return out


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


def parse_move(board, text):
    text = text.strip().strip(".,;:\"'`*")
    text = re.sub(r"^\d+\.(\.\.)?\s*", "", text)
    for parser in (board.parse_san, board.parse_uci):
        try:
            return parser(text)
        except ValueError:
            pass
    try:  # tolerate missing/extra check marks and castling spelled with zeros
        return board.parse_san(text.replace("0", "O").rstrip("+#"))
    except ValueError:
        return None


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
ANSWER: <the first move in standard algebraic notation, e.g. Nf3 or Qxf7#>
"""

ORDER = "KQRBNP"
NAMES = {"K": "King", "Q": "Queen", "R": "Rook", "B": "Bishop", "N": "Knight", "P": "Pawn"}


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
    )


def extract_answer(reply):
    hits = re.findall(r"ANSWER:\s*(\S+)", reply)
    return hits[-1] if hits else None


def make_claude_cli_asker(model):
    import os
    import subprocess

    env = {**os.environ, "MAX_THINKING_TOKENS": "0"}
    cmd = ["claude", "-p", "--model", model, "--tools", "",
           "--strict-mcp-config", "--system-prompt", "You are a helpful assistant."]

    def ask(prompt):
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, env=env, timeout=300)
        if r.returncode != 0:
            raise RuntimeError(f"claude CLI failed ({r.returncode}): {r.stderr.strip()}")
        return r.stdout

    return ask


def make_mock_asker(puzzles):
    by_prompt = {build_prompt(p): p["key"] for p in puzzles}
    return lambda prompt: f"ANSWER: {by_prompt[prompt]}"


def grade(p, reply):
    board = chess.Board(p["fen"])
    raw = extract_answer(reply)
    if raw is None:
        return False, "no ANSWER line"
    move = parse_move(board, raw)
    if move is None:
        return False, f"unparseable/illegal move {raw!r}"
    san = board.san(move)
    if forces_mate(board, move, p["mate_in"]):
        return True, san
    return False, f"{san} does not force mate in {p['mate_in']}"


def verify():
    ok = True
    for p in PUZZLES:
        board = chess.Board(p["fen"])
        n = p["mate_in"]
        keys = key_moves(board, n)
        shorter = mating_moves(board) if n == 2 else []
        stated = parse_move(board, p["key"])
        good = (
            stated in keys
            and len(keys) == 1
            and not shorter
            and not (n == 1 and False)
        )
        if n == 1:
            good = stated in keys and len(keys) == 1
        ok &= good
        print(f"{'OK ' if good else 'BAD'} {p['name']}: key={[board.san(m) for m in keys]} expected={p['key']}"
              + (f" (unexpected mate-in-1: {[board.san(m) for m in shorter]})" if shorter else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--show-reply", action="store_true")
    args = ap.parse_args()

    if args.verify:
        sys.exit(0 if verify() else 1)
    if not (args.model or args.mock):
        ap.error("pass --model, --mock or --verify")

    ask = make_mock_asker(PUZZLES) if args.mock else make_claude_cli_asker(args.model)
    total = passed = 0
    print(f"Model: {'mock' if args.mock else args.model}   runs/puzzle: {args.runs}\n")
    for p in PUZZLES:
        prompt = build_prompt(p)
        wins = 0
        notes = []
        for _ in range(args.runs):
            reply = ask(prompt)
            if args.show_reply:
                print(reply, "\n---")
            ok, note = grade(p, reply)
            wins += ok
            notes.append(note)
        total += args.runs
        passed += wins
        print(f"{'PASS' if wins == args.runs else 'FAIL'}  {p['name']}  (M{p['mate_in']})  {wins}/{args.runs}  {'; '.join(notes)}")
    print(f"\nScore: {passed}/{total}")


if __name__ == "__main__":
    main()
