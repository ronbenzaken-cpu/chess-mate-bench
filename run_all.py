#!/usr/bin/env python3
"""Full grid: 3 puzzles x 3 models x 2 thinking modes x 5 runs = 90 calls -> results.json + RESULTS.md

  .venv/bin/python run_all.py
"""
import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import bench

MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}
MODES = {"thinking=0": False, "thinking=default": True}
RUNS = 5
SOLVED_AT = 3  # a puzzle counts as "solved" by a model/mode if it passes at least 3 of 5 runs

# Hypotheses (see EXPECTATIONS.md): puzzle numbers each model/mode is expected to solve.
EXPECTED = {
    ("haiku", "thinking=0"): set(),
    ("haiku", "thinking=default"): {1},
    ("sonnet", "thinking=0"): {1},
    ("sonnet", "thinking=default"): {1, 2, 3},
    ("opus", "thinking=0"): {1, 2, 3},
    ("opus", "thinking=default"): {1, 2, 3},
}


def job(args):
    p, label, model, mode, thinking, run = args
    ask = bench.make_claude_cli_asker(model, thinking)
    try:
        reply = ask(bench.build_prompt(p))
        g = bench.grade(p, reply)
    except Exception as e:  # keep the grid going
        reply = ""
        g = {"pass": False, "category": "error", "first": None, "line_ok": False, "note": f"error: {e}"}
    return {"puzzle": p["name"], "mate_in": p["mate_in"], "model": label, "model_id": model,
            "mode": mode, "run": run, **g, "reply": reply}


def rows(results, **kw):
    return [r for r in results if all(r[k] == v for k, v in kw.items())]


def cell(results, key="pass", **kw):
    rs = rows(results, **kw)
    return f"{sum(r[key] for r in rs)}/{len(rs)}"


def solved(results, model, mode):
    return {i for i, p in enumerate(bench.PUZZLES, 1)
            if sum(r["pass"] for r in rows(results, puzzle=p["name"], model=model, mode=mode)) >= SOLVED_AT}


def fmt(puzzles):
    return ", ".join(map(str, sorted(puzzles))) or "none"


def write_md(results, path):
    combos = [(m, mode) for m in MODELS for mode in MODES]
    header = "| Puzzle | Mate in | " + " | ".join(f"{m} {mode}" for m, mode in combos) + " |"
    sep = "|---|---|" + "---|" * len(combos)
    L = ["# Results", "",
         f"{len(results)} calls: {len(bench.PUZZLES)} puzzles x {len(MODELS)} models x {len(MODES)} thinking modes x {RUNS} runs.",
         "Models: " + ", ".join(f"{k} = `{v}`" for k, v in MODELS.items()), "",
         f"## Expected vs actual (solved = at least {SOLVED_AT}/{RUNS} passes)", "",
         "| Model | Thinking | Expected to solve | Actually solved | Hypothesis |", "|---|---|---|---|---|"]
    for m, mode in combos:
        exp, act = EXPECTED[(m, mode)], solved(results, m, mode)
        L.append(f"| {m} | {mode} | {fmt(exp)} | {fmt(act)} | {'confirmed' if exp == act else 'rejected'} |")
    L.append("")
    for title, key in (("Pass rate (first move forces mate)", "pass"), ("Full line correct", "line_ok")):
        L += [f"## {title}", "", header, sep]
        for p in bench.PUZZLES:
            L.append(f"| {p['name']} | {p['mate_in']} | "
                     + " | ".join(cell(results, key, puzzle=p["name"], model=m, mode=mode) for m, mode in combos) + " |")
        L.append("")
    L += ["## Failure categories", "", "| Category | Count |", "|---|---|"]
    for cat, n in Counter(r["category"] for r in results if not r["pass"]).most_common():
        L.append(f"| {cat} | {n} |")
    L += ["", "## Failures", ""]
    for r in results:
        if not r["pass"]:
            L.append(f"- {r['puzzle']} | {r['model']} | {r['mode']} | run {r['run']} | {r['category']}: {r['note']}")
    open(path, "w").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    jobs = [(p, l, m, mode, th, r) for p in bench.PUZZLES for l, m in MODELS.items()
            for mode, th in MODES.items() for r in range(1, RUNS + 1)]
    with ThreadPoolExecutor(args.workers) as ex:
        results = list(ex.map(job, jobs))
    json.dump(results, open("results.json", "w"), indent=1)
    write_md(results, "RESULTS.md")
    print(f"{sum(r['pass'] for r in results)}/{len(results)} passed -> RESULTS.md")


if __name__ == "__main__":
    main()
