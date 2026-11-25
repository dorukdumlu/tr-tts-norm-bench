"""Score non-speech transcripts: what does each ASR write where nothing was said, and does it write a "yes"?

  python nonspeech/score.py nonspeech/clips.json nonspeech/results/*.json

For a non-speech clip, the transcript (event tags in () or [] removed) falls in one bucket, worst first:
  AFFIRM  an answer word: evet, hı hı, tamam, olur, peki, aynen, he, onaylıyorum, kabul ...
  NEG     hayır, yok, istemiyorum ...
  DIGITS  digits or number words (a wrong amount or code is as bad as a wrong yes in a bank flow)
  TEXT    any other words
  FILLER  hmm, ıı, eee, aa: harmless sounds
  EMPTY   nothing (correct)
Control clips must contain their expected words ("ctrl ok").
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

AFFIRM = {"evet", "hıhı", "ıhı", "ıhım", "hıhım", "mhm", "mhmm", "aha", "tamam", "olur", "peki", "aynen", "he", "hee",
          "heee", "onaylıyorum", "onaylarım", "kabul", "kabulediyorum", "doğru", "eyvallah", "tamamdır", "olsun"}
NEG = {"hayır", "yok", "istemiyorum", "olmaz", "hayir"}
FILLER = {"hmm", "hm", "hmmm", "ıı", "ııı", "ı", "eee", "ee", "e", "aa", "aaa", "a", "ah", "oh", "of", "off", "öhö",
          "ehe", "hı", "ha", "hah", "haha", "hahaha", "ehh", "ıh", "ay", "uh", "um", "mm", "mmm", "ım", "hıh", "ahh"}
NUMWORDS = {"sıfır", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz", "yirmi", "otuz",
            "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan", "yüz", "bin", "milyon"}
BUCKETS = ["AFFIRM", "NEG", "DIGITS", "TEXT", "FILLER", "EMPTY"]


def words(text):
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]|<[^>]*>", " ", text.lower())
    t = t.replace("i̇", "i")
    t = re.sub(r"\bhı[\s-]+hı\b", "hıhı", t)
    t = re.sub(r"\b(m+h+m+)\b", "mhm", t)
    return re.findall(r"[a-zçğıöşü0-9]+", t)


def bucket(text):
    w = words(text)
    if not w:
        return "EMPTY"
    s = set(w)
    if s & AFFIRM:
        return "AFFIRM"
    if s & NEG:
        return "NEG"
    if any(x.isdigit() for x in w) or s & NUMWORDS:
        return "DIGITS"
    if s <= FILLER:
        return "FILLER"
    return "TEXT"


def ctrl_ok(text, expect):
    got = " ".join("bir" if w == "1" else w for w in words(text))
    return all(x in got.split() or x in got for x in words(expect))


def main():
    meta = json.load(open(sys.argv[1], encoding="utf-8"))
    runs = {os.path.splitext(os.path.basename(p))[0]: json.load(open(p, encoding="utf-8")) for p in sys.argv[2:]}
    ns = [k for k, m in meta.items() if m["group"] != "ctrl"]
    ctrl = [k for k, m in meta.items() if m["group"] == "ctrl"]
    print(f"{len(ns)} non-speech clips, {len(ctrl)} controls\n")
    print("| ASR | empty | filler | other text | digits | no | **yes** | controls right | errors |")
    print("|---|---|---|---|---|---|---|---|---|")
    per_group = {}
    for name, out in runs.items():
        b = Counter(bucket(out[k]) for k in ns if k in out and not out[k].startswith("__ERROR__"))
        errs = sum(1 for k in meta if k in out and out[k].startswith("__ERROR__"))
        n = sum(b.values())
        c = sum(ctrl_ok(out.get(k, ""), meta[k]["expect"]) for k in ctrl)
        pct = lambda x: f"{b[x]} ({100 * b[x] / n:.0f}%)" if n else "-"
        print(f"| {name} | {pct('EMPTY')} | {pct('FILLER')} | {pct('TEXT')} | {pct('DIGITS')} | {pct('NEG')} | "
              f"**{pct('AFFIRM')}** | {c}/{len(ctrl)} | {errs} |")
        g = defaultdict(Counter)
        for k in ns:
            if k in out and not out[k].startswith("__ERROR__"):
                g[f"{meta[k]['group']}/{meta[k]['cls']}"][bucket(out[k])] += 1
        per_group[name] = g

    classes = sorted({c for g in per_group.values() for c in g})
    print("\nyes-word rate per class (AFFIRM / clips):\n")
    print("| class | " + " | ".join(runs) + " |")
    print("|---|" + "---|" * len(runs))
    for c in classes:
        cells = []
        for name in runs:
            cnt = per_group[name].get(c, Counter())
            tot = sum(cnt.values())
            cells.append(f"{cnt['AFFIRM']}/{tot}" if tot else "-")
        print(f"| {c} | " + " | ".join(cells) + " |")

    print("\nfailed controls:")
    for name, out in runs.items():
        bad = [f"{k}: {out.get(k, '')!r}" for k in ctrl if not ctrl_ok(out.get(k, ""), meta[k]["expect"])]
        if bad:
            print(f"  {name}: " + "; ".join(bad[:8]) + (" ..." if len(bad) > 8 else ""))


if __name__ == "__main__":
    main()
