#!/usr/bin/env python3
"""Score ASR transcripts against the accepted readings: are the numbers heard right?

  python asr/score_asr.py results/asr/*.json

A file is named <voice>__<asr>.json. A line counts when its number, month and unit words match an accepted reading
(bench/score.py); digits left in a transcript are expanded first (heard_right). "agree" counts lines every ASR of the same voice gets wrong: when they all fail, the audio itself is
the likely cause, not the ASR.
"""
import json
import os
import re
import sys
from collections import OrderedDict, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
from freyatts_main import spell_number  # noqa: E402
from score import judge  # noqa: E402

DIGIT = ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]


def ordinal(n):
    """12 -> "on ikinci": the suffix follows the vowel of the last word ("dört" -> "dördüncü")."""
    w = spell_number(n)
    last = w.split()[-1]
    v = [c for c in last if c in "aeıioöuü"][-1]
    suf = {"a": "ıncı", "ı": "ıncı", "e": "inci", "i": "inci", "o": "uncu", "u": "uncu", "ö": "üncü", "ü": "üncü"}[v]
    if last.endswith(tuple("aeıioöuü")):
        suf = suf[1:]  # "iki" -> "ikinci"
    return w[: -len(last)] + ("dörd" if last == "dört" else last) + suf


def heard_right(text, readings):
    """Digits an ASR still writes are read one by one ("0718"), or each run as a number ("2450"); either may match."""
    if not re.search(r"\d", text):
        return judge(text, readings)["numbers"]
    text = re.sub(r"(\d),(\d)", r"\1 virgül \2", text)  # "1,5 dakika"
    text = re.sub(r"(\d+)\.(?=\s+[a-zçğıöşü])", lambda m: f" {ordinal(int(m.group(1)))} ", text)  # "12. katında"
    one_by_one = re.sub(r"\d", lambda m: f" {DIGIT[int(m.group(0))]} ", text)
    as_numbers = re.sub(r"\d+", lambda m: f" {spell_number(int(m.group(0)))} ", text)
    return judge(one_by_one, readings)["numbers"] or judge(as_numbers, readings)["numbers"]


items = OrderedDict()
with open(os.path.join(ROOT, "data", "tr_customer_lines.jsonl"), encoding="utf-8") as f:
    for line in f:
        if line.strip():
            it = json.loads(line)
            items[it["id"]] = it
cats = list(OrderedDict.fromkeys(it["cat"] for it in items.values()))

runs = {}
for path in sys.argv[1:]:
    voice, asr = os.path.splitext(os.path.basename(path))[0].split("__")
    with open(path, encoding="utf-8") as f:
        heard = json.load(f)
    runs[(voice, asr)] = {k: heard_right(heard[k], items[k]["spoken"]) for k in items}

print("| voice | ASR | numbers heard right | " + " | ".join(cats) + " |")
print("|" + "---|" * (3 + len(cats)))
for (voice, asr), ok in runs.items():
    per = defaultdict(lambda: [0, 0])
    for k, v in ok.items():
        per[items[k]["cat"]][0] += v
        per[items[k]["cat"]][1] += 1
    cells = " | ".join(f"{per[c][0]}/{per[c][1]}" for c in cats)
    print(f"| {voice} | {asr} | {sum(ok.values())}/{len(ok)} | {cells} |")

by_voice = defaultdict(list)
for (voice, asr), ok in runs.items():
    by_voice[voice].append(ok)
for voice, oks in by_voice.items():
    if len(oks) > 1:
        all_fail = [k for k in items if not any(ok[k] for ok in oks)]
        print(f"\n{voice}: every ASR wrong on {len(all_fail)} lines: {', '.join(all_fail)}")
