"""One-off: add readings that are acceptable but were missing from the FreyaTTS eval set."""
import io
import json
import sys

path = sys.argv[1]
items = [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]
extra = {
    "money-06": ["İşlem ücreti sıfır lira elli kuruş."],
    "id-02": [
        "Havale için hesap numaranız te re on iki, sıfır sıfır sıfır altı, dört sıfır sıfır sıfır, sıfır sıfır bir bir, iki üç dört beş, altı yedi sekiz dokuz, sıfır bir.",
        "Havale için hesap numaranız TR on iki, sıfır sıfır sıfır altı, dört sıfır sıfır sıfır, sıfır sıfır bir bir, iki üç dört beş, altı yedi sekiz dokuz, sıfır bir.",
    ],
}
for it in items:
    for r in extra.get(it["id"], []):
        if r not in it["spoken"]:
            it["spoken"].append(r)
with io.open(path, "w", encoding="utf-8", newline="\n") as f:
    for it in items:
        f.write(json.dumps(it, ensure_ascii=False) + "\n")
print("ok", len(items))
