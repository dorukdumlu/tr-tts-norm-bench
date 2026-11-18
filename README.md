# tr-tts-norm-bench

A small benchmark for Turkish text normalization before text-to-speech: does the normalizer turn the numbers in
customer-facing text into what a careful human agent would say?

A TTS model given `Borcunuz 2450.75 TL` either reads the digits however it learned to or skips them. A
normalizer is supposed to turn it into `iki bin dört yüz elli lira yetmiş beş kuruş` first. This repo checks
six open-source Turkish normalizers on 67 lines a bank or insurer would send: dates, codes with leading zeros,
phone numbers, card numbers and IBANs, clock times, decimals and percentages, money, ordinals, symbols, and plain
sentences as a control.

## Results

`numbers right` = the number, month and unit words of the output match one accepted reading, in order, and no
digit is left. `exact` = every word matches. Case, punctuation and suffix apostrophes are ignored.

| normalizer | version | numbers right | exact | date | zeros | phone | ids | time | decimal | money | ordinal | symbols | control |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trnorm-js](https://github.com/ozguradmin/trnorm-js) | 0.1.3 | **65/67** | 63/67 | 8/8 | 6/6 | 6/6 | 3/5 | 8/8 | 7/7 | 8/8 | 5/5 | 6/6 | 8/8 |
| [turkce-normalize](https://github.com/seslen-tr/turkce-normalize) | 0.1.7 | 57/67 | 56/67 | 8/8 | 4/6 | 6/6 | 1/5 | 8/8 | 5/7 | 6/8 | 5/5 | 6/6 | 8/8 |
| [normalizer-tr](https://github.com/erdemtuna/normalizer-tr), `fallback` | 0.8.1 | 50/67 | 45/67 | 8/8 | 1/6 | 6/6 | 1/5 | 8/8 | 4/7 | 7/8 | 1/5 | 6/6 | 8/8 |
| [turkificate](https://github.com/eaysu/turkificate) | 0.2.0 | 46/67 | 44/67 | 8/8 | 0/6 | 1/6 | 0/5 | 6/8 | 5/7 | 7/8 | 5/5 | 6/6 | 8/8 |
| [normalizer-tr](https://github.com/erdemtuna/normalizer-tr), default `preserve` | 0.8.1 | 35/67 | 32/67 | 4/8 | 0/6 | 5/6 | 0/5 | 6/8 | 2/7 | 7/8 | 1/5 | 5/6 | 5/8 |
| [trnorm](https://github.com/ysdede/trnorm) (built for ASR scoring) | 0.1.0 | 27/67 | 23/67 | 0/8 | 0/6 | 1/6 | 0/5 | 6/8 | 3/7 | 4/8 | 5/5 | 3/6 | 5/8 |
| [FreyaTTS](https://github.com/freyavoiceai/FreyaTTS) built-in `normalize()` | 146d36c | 27/67 | 26/67 | 0/8 | 0/6 | 3/6 | 3/5 | 6/8 | 0/7 | 1/8 | 1/5 | 5/6 | 8/8 |

Every output is in `results/<normalizer>.jsonl`, next to the input and the expected reading.

## What goes wrong

| input | output | normalizer |
|---|---|---|
| `Kart numaranız 4543 1234 5678 9010.` | dört bin beş yüz kırk üç bin iki yüz otuz dört … | all six |
| `Poliçe numaranız 2024-118734.` | iki bin yirmi dört **ila** yüz on sekiz bin … (read as a range) | trnorm-js |
| `Doğrulama kodunuz 0718.` | sıfır yedi **yüz on sekiz** | turkce-normalize |
| `Toplam borcunuz 2450.75 TL.` | **iki yüz kırk beş bin** yetmiş beş lira | turkce-normalize, FreyaTTS |
| `Faiz oranı %3.5` | yüzde üç**.**beş | turkce-normalize |
| `Kartınızın son dört hanesi 0042.` | sıfır sıfır dört iki **nokta** | normalizer-tr `fallback` |
| `Kredinizin 3. taksiti` | **üç.** taksiti | normalizer-tr `fallback`, FreyaTTS |
| `Faiz oranı %3,49` | yüzde üç virgül **dört dokuz** | normalizer-tr |
| `Sizi saat 14.45'te arayacağız.` | saat on dört**.45**'te | turkificate |
| `Bizi 0850 222 23 35 numarasından` | **sekiz yüz elli** … (leading zero dropped) | turkificate, FreyaTTS |
| `Doğum tarihiniz 14.03.1988 mi?` | **on dört milyon otuz bir bin** … | FreyaTTS |
| `Kartınızın son dört hanesi 0042.` | **kırk ikinci** (read as an ordinal) | trnorm |

Notes on fairness:

- **normalizer-tr** by default leaves anything it finds ambiguous as written and reports it in `issues`, so the
  caller can decide. That is a deliberate design, and the default row mostly measures it. The `fallback` row is
  the library guessing.
- **trnorm** was built to normalize ASR references and hypotheses for WER, not to prepare TTS input. It is
  here because it comes up near the top of a GitHub search for Turkish normalization, not because it is meant
  for this job. It is not on PyPI; it is installed from GitHub.
- Each library is called through its documented top-level function with default options (`bench/adapters.py`).

## The lines

`data/tr_customer_lines.jsonl`: one line per object, with the written text and every reading accepted as right
(the first is the reference).

```json
{"id": "money-05", "cat": "money", "text": "Toplam borcunuz 2450.75 TL.",
 "spoken": ["Toplam borcunuz iki bin dört yüz elli lira yetmiş beş kuruş.",
            "Toplam borcunuz iki bin dört yüz elli virgül yetmiş beş lira."]}
```

Accepted readings follow how a call-center agent reads to a customer:

- codes and identifiers keep their leading zeros and are read digit by digit or in natural groups;
- dates are read with the month name;
- decimals are read as a number after "virgül" (`3,49` → üç virgül kırk dokuz);
- amounts in lira are read with kuruş, or with "virgül".

Where two readings are both normal, both are listed.

## Run it

```bash
python -m venv .venv
.venv/Scripts/python -m pip install normalizer-tr turkificate turkce-normalize git+https://github.com/ysdede/trnorm.git
cd js && npm install && cd ..
.venv/Scripts/python -X utf8 run.py
```

To add a normalizer, add a function to `bench/adapters.py` that takes a list of lines and returns a list of
outputs.

## Limits

- **67 lines, 5 to 8 per category.** One line is worth 1.5 points. Read the per-category columns and the
  failures, not only the total.
- **The lines and accepted readings were written by one person** (me), first for the FreyaTTS number-reading
  eval. Different readings can be right; if one of yours is marked wrong, open an issue and it will be added.
- **Text only.** It does not check how a TTS model then pronounces the text.
- **Banking and insurance text only.** No addresses, units, abbreviations, foreign names, URLs, plates or Roman
  numerals; several of these libraries handle those, and this benchmark says nothing about them.
- My own normalizer for FreyaTTS
  ([freyavoiceai/FreyaTTS#7](https://github.com/freyavoiceai/FreyaTTS/pull/7)) is left out: it was developed
  against these lines, so its score would mean nothing.

## License

Code: Apache-2.0. `bench/freyatts_main.py` is copied from FreyaTTS (Apache-2.0). The lines in `data/`:
CC-BY-4.0.
