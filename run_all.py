#!/usr/bin/env python3
"""Full grid for one persona: 3 puzzles x 3 models x 2 thinking modes x 5 runs = 90 calls.

  .venv/bin/python run_all.py                          # persona=assistant  -> results_assistant.json, RESULTS_assistant.md
  .venv/bin/python run_all.py --persona grandmaster    # persona=grandmaster -> results_grandmaster.json, RESULTS_grandmaster.md
"""
import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import bench

MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}
MODES = {"thinking=0": False, "thinking=default": True}
RUNS = 5


def job(args):
    p, label, model, mode, thinking, persona, run = args
    ask = bench.make_claude_cli_asker(model, thinking, persona)
    try:
        reply = ask(bench.build_prompt(p))
        g = bench.grade(p, reply)
    except Exception as e:  # keep the grid going
        reply = ""
        g = {"pass": False, "category": "error", "first": None, "line_ok": False, "note": f"error: {e}"}
    return {"puzzle": p["name"], "mate_in": p["mate_in"], "model": label, "model_id": model,
            "mode": mode, "persona": persona, "run": run, **g, "reply": reply}


def cell(results, key="pass", **kw):
    rs = [r for r in results if all(r[k] == v for k, v in kw.items())]
    return f"{sum(r[key] for r in rs)}/{len(rs)}"


def write_md(results, persona, path):
    combos = [(m, mode) for m in MODELS for mode in MODES]
    header = "| Puzzle | Mate in | " + " | ".join(f"{m} {mode}" for m, mode in combos) + " |"
    sep = "|---|---|" + "---|" * len(combos)
    L = ["# Results", "",
         f"Persona: **{persona}** (system prompt: \"{bench.PERSONAS[persona]}\")", "",
         f"{len(results)} calls: {len(bench.PUZZLES)} puzzles x {len(MODELS)} models x {len(MODES)} thinking modes x {RUNS} runs.",
         "Models: " + ", ".join(f"{k} = `{v}`" for k, v in MODELS.items()), ""]
    for title, key in (("Pass rate (first move forces mate)", "pass"), ("Full line correct", "line_ok")):
        L += [f"## {title}", "", header, sep]
        for p in bench.PUZZLES:
            L.append(f"| {p['name']} | {p['mate_in']} | "
                     + " | ".join(cell(results, key, puzzle=p["name"], model=m, mode=mode) for m, mode in combos) + " |")
        L.append("")
    L += ["## Totals", "", "| Model | " + " | ".join(MODES) + " |", "|---|" + "---|" * len(MODES)]
    for m in MODELS:
        L.append(f"| {m} | " + " | ".join(cell(results, model=m, mode=mode) for mode in MODES) + " |")
    L += ["", f"**Overall: {sum(r['pass'] for r in results)}/{len(results)}**", "",
          "## Failure categories", "", "| Category | Count |", "|---|---|"]
    for cat, n in Counter(r["category"] for r in results if not r["pass"]).most_common():
        L.append(f"| {cat} | {n} |")
    L += ["", "## Failures", ""]
    for r in results:
        if not r["pass"]:
            L.append(f"- {r['puzzle']} | {r['model']} | {r['mode']} | run {r['run']} | {r['category']}: {r['note']}")
    open(path, "w").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", choices=bench.PERSONAS, default="assistant")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    jobs = [(p, l, m, mode, th, args.persona, r) for p in bench.PUZZLES for l, m in MODELS.items()
            for mode, th in MODES.items() for r in range(1, RUNS + 1)]
    with ThreadPoolExecutor(args.workers) as ex:
        results = list(ex.map(job, jobs))
    json.dump(results, open(f"results_{args.persona}.json", "w"), indent=1)
    write_md(results, args.persona, f"RESULTS_{args.persona}.md")
    print(f"{sum(r['pass'] for r in results)}/{len(results)} passed -> RESULTS_{args.persona}.md")


if __name__ == "__main__":
    main()
