"""v0.2 of the lines: replace two lines no bank would say, accept both common readings of a decimal fraction."""
import io
import json
import sys

path = sys.argv[1]
items = [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]
by_id = {it["id"]: it for it in items}

# A bank does not read a full card number to a customer (PCI DSS masks it). A cargo tracking number is read.
by_id["id-01"].update({
    "text": "Kargo takip numaranız 7340 1129 58.",
    "spoken": ["Kargo takip numaranız yedi üç dört sıfır, bir bir iki dokuz, beş sekiz.",
               "Kargo takip numaranız yetmiş üç kırk, on bir yirmi dokuz, elli sekiz."],
})
# A door code is not something a bank or insurer says. A one-time code read aloud is.
by_id["zero-06"].update({
    "text": "Tek kullanımlık şifreniz 0905.",
    "spoken": ["Tek kullanımlık şifreniz sıfır dokuz sıfır beş.", "Tek kullanımlık şifreniz sıfır dokuz sıfır beş."],
})
by_id["zero-06"]["spoken"] = by_id["zero-06"]["spoken"][:1]

# Digit by digit after "virgül" is less common for rates, but not wrong.
extra = {
    "dec-01": "Faiz oranı yüzde üç virgül dört dokuz olarak güncellendi.",
    "dec-05": "Dolar kuru otuz dört virgül yedi beş seviyesinde.",
    "dec-07": "Komisyon oranı yüzde sıfır virgül iki beş.",
}
for k, r in extra.items():
    if r not in by_id[k]["spoken"]:
        by_id[k]["spoken"].append(r)

with io.open(path, "w", encoding="utf-8", newline="\n") as f:
    for it in items:
        f.write(json.dumps(it, ensure_ascii=False) + "\n")
print("ok", len(items))
