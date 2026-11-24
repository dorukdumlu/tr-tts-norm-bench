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
| [turkce-normalize](https://github.com/seslen-tr/turkce-normalize) | 0.1.11 | 61/67 | 8/8 | 6/6 | 6/6 | 1/5 | 8/8 | 5/7 | 8/8 | 5/5 | 6/6 | 8/8 |
| [normalizer-tr](https://github.com/erdemtuna/normalizer-tr) `fallback` | 0.8.2 | 59/67 | 8/8 | 6/6 | 6/6 | 2/5 | 8/8 | 7/7 | 7/8 | 1/5 | 6/6 | 8/8 |
| [turkificate](https://github.com/eaysu/turkificate) | 0.2.0 | 46/67 | 8/8 | 0/6 | 1/6 | 0/5 | 6/8 | 5/7 | 7/8 | 5/5 | 6/6 | 8/8 |
| [normalizer-tr](https://github.com/erdemtuna/normalizer-tr) default | 0.8.2 | 38/67 | 4/8 | 0/6 | 5/6 | 0/5 | 6/8 | 5/7 | 7/8 | 1/5 | 5/6 | 5/8 |
| [trnorm](https://github.com/ysdede/trnorm) | 0.1.0 | 27/67 | 0/8 | 0/6 | 1/6 | 0/5 | 6/8 | 3/7 | 4/8 | 5/5 | 3/6 | 5/8 |
| FreyaTTS built-in | 146d36c | 27/67 | 0/8 | 0/6 | 3/6 | 3/5 | 6/8 | 0/7 | 1/8 | 1/5 | 5/6 | 8/8 |

So yes: trnorm-js would have done almost all of it. Two caveats on the others. normalizer-tr by default leaves
anything ambiguous as written and reports it to the caller, on purpose; the `fallback` row is the library
guessing. trnorm was built to normalize ASR transcripts for WER, not TTS input.

Since this was first published, turkce-normalize (0.1.8 to 0.1.11) and normalizer-tr (0.8.2) fixed several of the
failures below; the table above is re-run on those versions.

Some of what goes wrong (every output is in `results/`):

| written | read as | by |
|---|---|---|
| `Kargo takip numaranız 7340 1129 58.` | yedi bin üç yüz **kırk bin** yüz yirmi dokuz… | all |
| `Toplam borcunuz 2450.75 TL.` | **iki yüz kırk beş bin** yetmiş beş lira | FreyaTTS; turkce-normalize until 0.1.7 |
| `Poliçe numaranız 2024-118734.` | iki bin yirmi dört **ila** yüz on sekiz bin… | trnorm-js |
| `Doğrulama kodunuz 0718.` | sıfır **yedi yüz on sekiz** | turkce-normalize until 0.1.10 |
| `Faiz oranı %3.5` | yüzde **üç.beş** | turkce-normalize |
| `Kartınızın son dört hanesi 0042.` | sıfır sıfır dört iki **nokta** | normalizer-tr `fallback` until 0.8.1 |
| `Kredinizin 3. taksiti` | **üç.** taksiti | normalizer-tr `fallback`, FreyaTTS |
| `Bizi 0850 222 23 35 numarasından` | **sekiz yüz elli**… | turkificate, FreyaTTS |
| `Sizi saat 14.45'te arayacağız.` | saat **on dört.45**'te | turkificate |

## The other direction: does an ASR hear the numbers on a phone line?

The same lines, read aloud and band-limited to 8 kHz (telephone), then transcribed. Each voice reads the first
accepted reading, already spelled out, so text normalization plays no part. A line counts when the number, month
and unit words heard match an accepted reading.

| ASR | 4 Google voices (268 utterances) | FreyaTTS (67) |
|---|---|---|
| [balbal-v2](https://github.com/erayyap/balbal) 0.6.11 | **267** | 46 |
| balbal-v2-manas | **267** | 47 |
| Whisper large-v3-turbo | 263 | 44 |
| Whisper medium | 261 | 43 |

Voices: Google `tr-TR-Standard-A`, `Wavenet-E`, `Chirp3-HD-Kore`, `Chirp3-HD-Charon`. Per voice and category:
[results/asr/SUMMARY.md](results/asr/SUMMARY.md); every transcript is in `results/asr/`.

- **On clean speech, numbers are not the ASR's problem.** Every ASR hears 97% or more. The one line balbal misses
  (`Yıllık aidat 10,00 TL`, read "aidat on lira") is heard as "aidat **ton** lira" by both balbal models and Whisper medium on the
  Standard-A voice: the "t" of "aidat" runs into "on". Whisper turbo writes "10 lira".
- **Whisper's remaining errors are runs of zeros.** `TR12 0006 4000 …` comes back as `TR12 00006 40000 …`, and
  `0532 000 00 01` loses or gains a zero. balbal gets every IBAN and phone number right.
- **With FreyaTTS audio the ASRs fail on the same 12 lines**, all phone numbers and IBANs among them. For
  `Sizi saat 14.45'te` all four hear an extra "beş" ("kırk beş **beşte**") and three hear "saat **saat**"; three of four drop "kırk" from
  "üç virgül kırk dokuz": the audio itself repeats or skips, so those failures are the TTS, not the ASR.

How Whisper was run matters. Suppressing its number tokens (a common trick to make it write words) made
large-v3-turbo decode `!!!!` in float16 and, in float32, prepend junk and repeat sentences. The numbers above
use a prompt written with spelled-out numbers that occur nowhere in the data instead; digits Whisper still writes
are read one by one or as a number, and either may match (`asr/score_asr.py`).

Limits: synthetic speech is clean and clearly paced, real callers are not. No noise, no codec (μ-law), no packet
loss. This says the models can hear Turkish numbers on a phone-band signal, not that they will on a real call.

```bash
python asr/synth_google.py --voice tr-TR-Wavenet-E --out audio/google-wavenet-e   # Google ADC credentials
python asr/transcribe.py balbal --audio audio/google-wavenet-e --out results/asr/google-wavenet-e__balbal-v2.json
python asr/transcribe.py whisper --model medium --audio audio/google-wavenet-e --out results/asr/google-wavenet-e__whisper-medium.json
python asr/score_asr.py results/asr/*.json
```

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
