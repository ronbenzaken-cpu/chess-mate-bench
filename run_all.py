#!/usr/bin/env python3
"""Full grid: 3 puzzles x 3 models x 2 thinking modes x 5 runs = 90 calls -> results.json + RESULTS.md"""
import json
from concurrent.futures import ThreadPoolExecutor

import bench

MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}
MODES = {"thinking=0": False, "thinking=default": True}
RUNS = 5


def job(args):
    p, label, model, mode, thinking, run = args
    ask = bench.make_claude_cli_asker(model, thinking)
    try:
        reply = ask(bench.build_prompt(p))
        ok, note = bench.grade(p, reply)
    except Exception as e:  # keep the grid going
        reply, ok, note = "", False, f"error: {e}"
    return {"puzzle": p["name"], "mate_in": p["mate_in"], "model": label, "model_id": model,
            "mode": mode, "run": run, "pass": ok, "note": note, "reply": reply}


def main():
    jobs = [(p, l, m, mode, th, r) for p in bench.PUZZLES for l, m in MODELS.items()
            for mode, th in MODES.items() for r in range(1, RUNS + 1)]
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(job, jobs))
    json.dump(results, open("results.json", "w"), indent=1)
    write_md(results)


def cell(results, **kw):
    rs = [r for r in results if all(r[k] == v for k, v in kw.items())]
    return f"{sum(r['pass'] for r in rs)}/{len(rs)}"


def write_md(results):
    L = ["# Results", "", f"{len(results)} calls: {len(bench.PUZZLES)} puzzles x {len(MODELS)} models x {len(MODES)} modes x {RUNS} runs.",
         "Models: " + ", ".join(f"{k} = `{v}`" for k, v in MODELS.items()), ""]
    L += ["## Pass rate per puzzle", "", "| Puzzle | Mate in | " + " | ".join(f"{m} {mode}" for m in MODELS for mode in MODES) + " |",
          "|---|---|" + "---|" * (len(MODELS) * len(MODES))]
    for p in bench.PUZZLES:
        L.append(f"| {p['name']} | {p['mate_in']} | " + " | ".join(cell(results, puzzle=p["name"], model=m, mode=mode) for m in MODELS for mode in MODES) + " |")
    L += ["", "## Totals (out of 15 per cell)", "", "| Model | " + " | ".join(MODES) + " |", "|---|" + "---|" * len(MODES)]
    for m in MODELS:
        L.append(f"| {m} | " + " | ".join(cell(results, model=m, mode=mode) for mode in MODES) + " |")
    L += ["", f"**Overall: {sum(r['pass'] for r in results)}/{len(results)}**", "", "## Failures", ""]
    for r in results:
        if not r["pass"]:
            L.append(f"- {r['puzzle']} | {r['model']} | {r['mode']} | run {r['run']}: {r['note']}")
    open("RESULTS.md", "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
