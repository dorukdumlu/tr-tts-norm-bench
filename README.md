# tr-tts-norm-bench

I was fixing number reading in [FreyaTTS](https://github.com/freyavoiceai/FreyaTTS), a Turkish TTS model. Its
built-in normalizer turned `Toplam borcunuz 2450.75 TL` into "iki yüz kırk beş bin yetmiş beş TL" and a birth
date `14.03.1988` into "on dört milyon otuz bir bin…". For a bank's voice agent that is not a pronunciation
problem: the customer hears the wrong debt.

I wrote 67 lines a bank or insurer would actually say, with the readings an agent would give, to test my fix
([FreyaTTS#7](https://github.com/freyavoiceai/FreyaTTS/pull/7)). Then I wanted to know whether I should have
used an existing library instead. This repo runs the same lines through the open-source Turkish normalizers I
could find.

## Results

A line counts as right when its number, month and unit words match an accepted reading and no digit is left in
the output. Case, punctuation and suffix apostrophes are ignored.

| normalizer | version | right | date | zeros | phone | ids | time | decimal | money | ordinal | symbols | control |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [trnorm-js](https://github.com/ozguradmin/trnorm-js) | 0.1.3 | **65/67** | 8/8 | 6/6 | 6/6 | 3/5 | 8/8 | 7/7 | 8/8 | 5/5 | 6/6 | 8/8 |
| [turkce-normalize](https://github.com/seslen-tr/turkce-normalize) | 0.1.7 | 57/67 | 8/8 | 4/6 | 6/6 | 1/5 | 8/8 | 5/7 | 6/8 | 5/5 | 6/6 | 8/8 |
| [normalizer-tr](https://github.com/erdemtuna/normalizer-tr) `fallback` | 0.8.1 | 53/67 | 8/8 | 1/6 | 6/6 | 1/5 | 8/8 | 7/7 | 7/8 | 1/5 | 6/6 | 8/8 |
| [turkificate](https://github.com/eaysu/turkificate) | 0.2.0 | 46/67 | 8/8 | 0/6 | 1/6 | 0/5 | 6/8 | 5/7 | 7/8 | 5/5 | 6/6 | 8/8 |
| [normalizer-tr](https://github.com/erdemtuna/normalizer-tr) default | 0.8.1 | 38/67 | 4/8 | 0/6 | 5/6 | 0/5 | 6/8 | 5/7 | 7/8 | 1/5 | 5/6 | 5/8 |
| [trnorm](https://github.com/ysdede/trnorm) | 0.1.0 | 27/67 | 0/8 | 0/6 | 1/6 | 0/5 | 6/8 | 3/7 | 4/8 | 5/5 | 3/6 | 5/8 |
| FreyaTTS built-in | 146d36c | 27/67 | 0/8 | 0/6 | 3/6 | 3/5 | 6/8 | 0/7 | 1/8 | 1/5 | 5/6 | 8/8 |

So yes: trnorm-js would have done almost all of it. Two caveats on the others. normalizer-tr by default leaves
anything ambiguous as written and reports it to the caller, on purpose; the `fallback` row is the library
guessing. trnorm was built to normalize ASR transcripts for WER, not TTS input.

Some of what goes wrong (every output is in `results/`):

| written | read as | by |
|---|---|---|
| `Kargo takip numaranız 7340 1129 58.` | yedi bin üç yüz **kırk bin** yüz yirmi dokuz… | all |
| `Toplam borcunuz 2450.75 TL.` | **iki yüz kırk beş bin** yetmiş beş lira | turkce-normalize, FreyaTTS |
| `Poliçe numaranız 2024-118734.` | iki bin yirmi dört **ila** yüz on sekiz bin… | trnorm-js |
| `Doğrulama kodunuz 0718.` | sıfır **yedi yüz on sekiz** | turkce-normalize |
| `Faiz oranı %3.5` | yüzde **üç.beş** | turkce-normalize |
| `Kartınızın son dört hanesi 0042.` | sıfır sıfır dört iki **nokta** | normalizer-tr `fallback` |
| `Kredinizin 3. taksiti` | **üç.** taksiti | normalizer-tr `fallback`, FreyaTTS |
| `Bizi 0850 222 23 35 numarasından` | **sekiz yüz elli**… | turkificate, FreyaTTS |
| `Sizi saat 14.45'te arayacağız.` | saat **on dört.45**'te | turkificate |

## The lines

`data/tr_customer_lines.jsonl` has the written line and every reading I accept, for example:

```json
{"id": "money-05", "cat": "money", "text": "Toplam borcunuz 2450.75 TL.",
 "spoken": ["Toplam borcunuz iki bin dört yüz elli lira yetmiş beş kuruş.",
            "Toplam borcunuz iki bin dört yüz elli virgül yetmiş beş lira."]}
```

The readings are my judgment, not a standard. The ones a reader may disagree with:

- Codes with a leading zero are read digit by digit or in pairs: `0718` is "sıfır yedi bir sekiz", not "sıfır
  yedi yüz on sekiz".
- Tracking and policy numbers are read digit by digit or in pairs, not as one large number.
- After "virgül", both "üç virgül kırk dokuz" and "üç virgül dört dokuz" are accepted.

If you think a reading is marked wrong unfairly, open an issue; it is a one-line change.

## Run it

```bash
python -m venv .venv
.venv/Scripts/python -m pip install normalizer-tr turkificate turkce-normalize git+https://github.com/ysdede/trnorm.git
cd js && npm install && cd ..
.venv/Scripts/python -X utf8 run.py
```

A normalizer is one function in `bench/adapters.py`: a list of lines in, a list of lines out.

## Limits

67 lines is small: one line moves a score by 1.5 points, and the top of the table is close to the ceiling. The
lines come from banking and insurance only (no addresses, units, abbreviations, plates or foreign names, which
several of these libraries also handle). It checks text, not how a TTS model then pronounces it. My own FreyaTTS
normalizer is not in the table, because it was written against these lines.

## License

Code Apache-2.0 (`bench/freyatts_main.py` is copied from FreyaTTS, also Apache-2.0). Lines in `data/`: CC-BY-4.0.
