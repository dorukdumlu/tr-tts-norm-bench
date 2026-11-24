#!/usr/bin/env python3
"""Synthesize the reference reading of every line with FreyaTTS and write 8 kHz telephone-band WAVs.

The TTS gets the reading already spelled out (the first accepted reading), so its own normalizer plays no part.

  python asr/synth_freyatts.py --freyatts ../FreyaTTS --out audio/freyatts
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data", "tr_customer_lines.jsonl")
PHONE_SR = 8000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freyatts", required=True, help="a FreyaTTS checkout")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=None, help="voice seed (default: the model's)")
    args = ap.parse_args()

    sys.path.insert(0, args.freyatts)
    import librosa
    import soundfile as sf
    from freyatts import FreyaTTS

    tts = FreyaTTS.from_pretrained("freyavoice/freya-tts", device="cuda")
    os.makedirs(args.out, exist_ok=True)
    with open(DATA, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]
    for item in items:
        path = os.path.join(args.out, item["id"] + ".wav")
        if os.path.exists(path):
            continue
        kw = {} if args.seed is None else {"seed": args.seed}
        wav = tts.synthesize(item["spoken"][0], **kw)
        phone = librosa.resample(wav.astype("float32"), orig_sr=tts.sample_rate, target_sr=PHONE_SR)
        sf.write(path, phone, PHONE_SR)
        print(item["id"], round(len(phone) / PHONE_SR, 1), "s", flush=True)


if __name__ == "__main__":
    main()
