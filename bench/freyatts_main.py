"""normalize() from FreyaTTS (https://github.com/freyavoiceai/FreyaTTS), freyatts/pipeline.py at commit
146d36c, copied without changes so it can run without torch. Apache License 2.0, Copyright the FreyaTTS authors.
"""

import re

# English/foreign words the character vocabulary cannot pronounce as written;
# transliterated to Turkish phonetics. SFT already teaches common Turkish
# acronyms natively, so acronyms are left untouched.
BRAND = {
    "platinum": "platinyum",
    "mastercard": "mastırkard",
    "visa": "viza",
    "signature": "siğnetçır",
    "american express": "amerikan ekspres",
    "qr kod": "kju ar kod",
    "online": "onlayn",
    "mobil": "mobil",
}

_UNITS = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
_TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
_SCALES = [(10 ** 9, "milyar"), (10 ** 6, "milyon"), (10 ** 3, "bin")]


def spell_number(n):
    """Spell a non-negative integer in Turkish (0 -> 'sıfır')."""
    if n == 0:
        return "sıfır"
    parts = []
    for scale, name in _SCALES:
        if n >= scale:
            head = n // scale
            n = n % scale
            # Turkish drops the leading 'bir' before 'bin'
            if not (scale == 1000 and head == 1):
                parts.append(spell_number(head))
            parts.append(name)
    if n >= 100:
        if n // 100 > 1:
            parts.append(_UNITS[n // 100])
        parts.append("yüz")
        n = n % 100
    if n >= 10:
        parts.append(_TENS[n // 10])
        n = n % 10
    if n > 0:
        parts.append(_UNITS[n])
    return " ".join(parts)


def expand_digits(text):
    """Rewrite digit runs in their spoken Turkish form.

    A digit string is orthographically short but phonetically long, and the
    duration head sizes the utterance from the character sequence, so numbers
    left as digits come out truncated. Spelling them out before synthesis is
    part of the input contract. Clock times read as hour then minute, long
    account-style strings digit by digit, everything else as an integer.
    """
    def spoken(match):
        s = match.group(0)
        if ":" in s:
            hour, minute = s.split(":")
            out = spell_number(int(hour))
            if int(minute):
                out += " " + spell_number(int(minute))
            return out
        if len(s) >= 6 and "." not in s:
            return " ".join(spell_number(int(ch)) for ch in s)
        return spell_number(int(s.replace(".", "")))

    return re.sub(r"\d+:\d+|\d+(?:\.\d+)*", spoken, text)


def normalize(text):
    """Light text normalization: transliterate foreign words, spell out digit
    runs, collapse punctuation."""
    t = text
    for k in sorted(BRAND, key=len, reverse=True):
        t = re.sub(r"(?i)\b" + re.escape(k) + r"\b", BRAND[k], t)

    t = expand_digits(t)
    t = t.replace("...", ", ").replace("…", ", ").replace(" — ", ", ").replace(" - ", ", ")
    t = re.sub(r"\s+", " ", t).strip()
    return t
