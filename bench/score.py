"""Compare a normalizer's output with the accepted spoken readings of a line.

Two checks per line:

  exact    every word matches one accepted reading. Case, punctuation and apostrophes are ignored
           ("beş'te" = "beşte"), "TL" counts as "lira", and fused number words are split ("onbeş" = "on beş").
  numbers  the number, month and unit words match one accepted reading, in order. Case endings on them are
           ignored ("beşte" -> beş), but an ordinal keeps a mark ("üçüncü" -> üç.) so it never passes as the
           cardinal. A line can pass this and fail "exact" on wording outside the numbers.
"""

import re

NUMBER_WORDS = ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz", "on", "yirmi",
                "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan", "yüz", "bin", "milyon", "milyar"]
MONTHS = ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım",
          "aralık"]
UNIT_WORDS = ["virgül", "nokta", "buçuk", "yüzde", "lira", "kuruş", "artı"]
KEY_WORDS = set(NUMBER_WORDS) | set(MONTHS) | set(UNIT_WORDS)

_longest_first = sorted(NUMBER_WORDS, key=len, reverse=True)
_NUMBER = re.compile("|".join(_longest_first))
_FUSED = re.compile("(?:" + "|".join(_longest_first) + ")+")
_STEM = re.compile("(" + "|".join(sorted(NUMBER_WORDS + ["dörd"] + MONTHS + ["lira", "kuruş"], key=len,
                                         reverse=True)) + ")(.+)")
_ORDINAL = re.compile(r"[ıiuü]?nc[ıiuü].*")
_CASE = re.compile(r"[dt][ae]n?|y?[aeıiuü]|n?[ıiuü]n|y?l[ae]|[sş]?[ae]r|l[ıiuü]k|s[ıiuü]")


def words(text):
    """Lowercase word list: punctuation and suffix apostrophes dropped, "onbeş" -> on beş, "tl" -> lira."""
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = t.replace("â", "a").replace("î", "i").replace("û", "u")
    t = re.sub(r"['’`´]", "", t)
    t = re.sub(r"[^a-zçğıöşü0-9]+", " ", t)
    out = []
    toks = t.split()
    for i, w in enumerate(toks):
        if w == "tl":
            w = "lira"
        if w == "türk" and i + 1 < len(toks) and toks[i + 1].startswith("lira"):
            continue  # "Türk lirası" is "lira"
        if w.startswith("liras") and i > 0 and toks[i - 1] == "türk":
            w = "lira" + w[len("liras") + 1:]  # lirası -> lira, lirasını -> liranı is close enough
        out.extend(_NUMBER.findall(w) if _FUSED.fullmatch(w) else [w])
    return out


def key(tokens):
    """The number, month and unit words of a word list, case endings dropped; ordinals marked with a dot."""
    out = []
    for w in tokens:
        if w in KEY_WORDS:
            out.append(w)
            continue
        m = _STEM.fullmatch(w)
        if not m:
            continue
        stem = "dört" if m.group(1) == "dörd" else m.group(1)
        if _ORDINAL.fullmatch(m.group(2)):
            out.append(stem + ".")
        elif _CASE.fullmatch(m.group(2)):
            out.append(stem)
    return out


def has_digits(text):
    return bool(re.search(r"\d", text))


def judge(output, readings):
    hyp = words(output)
    refs = [words(r) for r in readings]
    return {"exact": hyp in refs, "numbers": not has_digits(output) and key(hyp) in [key(r) for r in refs]}
