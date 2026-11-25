"""How much of the false "yes" can an agent remove with signals the ASR already returns, and what does it cost?

  python nonspeech/gate_eval.py nonspeech/clips.json nonspeech/results/confidence/*.json

For each engine and rule: false-yes on non-speech clips (k/n, Wilson 95% CI), and how many real yes-answers in the
controls are still accepted (evet, tamam, olur, "evet, onaylıyorum", alone or after a cough).
Rules:
  text       any yes-word in the transcript (what a naive agent does)
  strict     only "evet" together with "onaylıyorum"/"onaylarım"/"kabul ediyorum" counts
  conf>=t    a yes-word counts only if its word confidence is at least t
  no_speech  balbal: drop when no_speech is true; Whisper: drop when no_speech_prob > 0.6
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import AFFIRM, bucket, words  # noqa: E402

YES_CTRL = ("evet", "tamam", "olur", "evet-onay", "cough+evet", "cough+tamam")


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


def yes_conf(rec):
    """Highest confidence among the words that make the yes (hı + hı counts as one)."""
    best = None
    for w, c in rec.get("words", []):
        toks = words(w)
        if any(t in AFFIRM or t == "hı" for t in toks) and c is not None:
            best = c if best is None else max(best, c)
    return best


def strict(text):
    t = " ".join(words(text))
    return "evet" in t.split() and bool(re.search(r"onaylıyorum|onaylarım|kabul ediyorum", t))


def main():
    meta = json.load(open(sys.argv[1], encoding="utf-8"))
    for path in sys.argv[2:]:
        name = os.path.splitext(os.path.basename(path))[0]
        rec = {k: v for k, v in json.load(open(path, encoding="utf-8")).items() if "error" not in v}
        ns = [k for k in rec if meta[k]["group"] != "ctrl"]
        yc = [k for k in rec if meta[k]["group"] == "ctrl" and meta[k]["cls"] in YES_CTRL]
        onay = [k for k in yc if meta[k]["cls"] == "evet-onay"]
        rules = {"text": lambda r: bucket(r["text"]) == "AFFIRM", "strict": lambda r: strict(r["text"])}
        has_conf = any(yes_conf(r) is not None for r in rec.values())
        if has_conf:
            for t in (0.3, 0.5, 0.7, 0.9):
                rules[f"conf>={t}"] = (lambda t: lambda r: bucket(r["text"]) == "AFFIRM" and (yes_conf(r) or 0) >= t)(t)
        if any("no_speech" in r for r in rec.values()):
            rules["no_speech"] = lambda r: bucket(r["text"]) == "AFFIRM" and not r.get("no_speech")
        if any("no_speech_prob" in r for r in rec.values()):
            rules["no_speech"] = lambda r: bucket(r["text"]) == "AFFIRM" and r.get("no_speech_prob", 1) <= 0.6
        print(f"\n### {name}  ({len(ns)} non-speech, {len(yc)} yes-controls, of which {len(onay)} full consent)")
        print("| rule | false yes | 95% CI | real yes kept | full consent kept |")
        print("|---|---|---|---|---|")
        for rn, f in rules.items():
            k = sum(f(rec[x]) for x in ns)
            lo, hi = wilson(k, len(ns))
            kept = sum(f(rec[x]) for x in yc)
            ko = sum(f(rec[x]) for x in onay)
            print(f"| {rn} | {k}/{len(ns)} ({100 * k / len(ns):.1f}%) | {100 * lo:.1f}-{100 * hi:.1f}% | "
                  f"{kept}/{len(yc)} | {ko}/{len(onay)} |")


if __name__ == "__main__":
    main()
