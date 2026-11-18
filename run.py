#!/usr/bin/env python3
"""Run every normalizer over the benchmark lines and write the results.

Usage:
  python -X utf8 run.py                      # all normalizers -> results/
  python -X utf8 run.py --only turkificate   # one normalizer
"""

import argparse
import json
import os
import sys
import time
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "bench"))

from adapters import ADAPTERS, versions  # noqa: E402
from score import judge  # noqa: E402

DATA = os.path.join(HERE, "data", "tr_customer_lines.jsonl")


def load():
    with open(DATA, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append")
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    args = ap.parse_args()

    items = load()
    cats = list(OrderedDict.fromkeys(i["cat"] for i in items))
    names = args.only or list(ADAPTERS)
    vers = versions()
    os.makedirs(args.out, exist_ok=True)

    summary = []
    for name in names:
        t0 = time.perf_counter()
        outputs = ADAPTERS[name]([i["text"] for i in items])
        ms = (time.perf_counter() - t0) * 1000
        rows = []
        for item, out in zip(items, outputs):
            v = judge(out, item["spoken"])
            rows.append({"id": item["id"], "cat": item["cat"], "text": item["text"], "output": out,
                         "expected": item["spoken"][0], **v})
        slug = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        with open(os.path.join(args.out, slug + ".jsonl"), "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        per_cat = {c: [sum(r["numbers"] for r in rows if r["cat"] == c), sum(1 for r in rows if r["cat"] == c)]
                   for c in cats}
        summary.append({"name": name, "version": vers.get(name, "?"), "numbers": sum(r["numbers"] for r in rows),
                        "exact": sum(r["exact"] for r in rows), "n": len(rows), "per_cat": per_cat,
                        "ms": round(ms, 1)})

    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    head = "| normalizer | version | numbers right | exact | " + " | ".join(cats) + " |"
    print(head)
    print("|" + "---|" * (4 + len(cats)))
    for s in sorted(summary, key=lambda s: -s["numbers"]):
        cells = " | ".join(f"{a}/{b}" for a, b in s["per_cat"].values())
        print(f"| {s['name']} | {s['version']} | {s['numbers']}/{s['n']} | {s['exact']}/{s['n']} | {cells} |")


if __name__ == "__main__":
    main()
