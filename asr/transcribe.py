#!/usr/bin/env python3
"""Transcribe a folder of 8 kHz WAVs (one per line id) with one ASR and write {id: transcript} as JSON.

  balbal:  python asr/transcribe.py balbal  --audio audio/freyatts --out results/asr/freyatts__balbal.json
  whisper: python asr/transcribe.py whisper --model medium --audio ... --out ...

Numbers are kept as spoken words where the ASR allows it: balbal --no-itn, and for Whisper a prompt written with
spelled-out numbers that do not occur in the data (PROMPT). Suppressing Whisper's number tokens instead
(--style suppress) makes large-v3-turbo prepend junk and repeat sentences, so it is not the default. Digits an ASR
still writes are handled by score_asr.py.
"""
import argparse
import glob
import json
import os
import subprocess
import sys


def balbal(files, args):
    exe = os.path.join(os.path.dirname(sys.executable), "balbal")
    out = {}
    proc = subprocess.run([exe, "run", "--no-itn", "--json", "--model", args.model or "v2", *files],
                          capture_output=True, text=True, encoding="utf-8", check=True)
    rows = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith("{")]
    for f, row in zip(files, rows):
        out[os.path.splitext(os.path.basename(f))[0]] = row["text"]
    return out


PROMPT = ("Sayıları yazıyla yazıyoruz: yirmi yedi nisan bin dokuz yüz doksan bir, sıfır dört yüz on altı, "
          "yüzde altı virgül iki, bin üç yüz on lira kırk kuruş.")


def whisper(files, args):
    import librosa
    from faster_whisper import WhisperModel

    # large-v3-turbo with the number tokens suppressed decodes only "!!!!" in float16; float32 is fine
    model = WhisperModel(args.model or "medium", device="cuda", compute_type=args.compute_type)
    tok = model.hf_tokenizer
    numerals = [i for i in range(tok.get_vocab_size()) if any(c.isdigit() for c in tok.decode([i]))]
    out = {}
    for f in files:
        wav, _ = librosa.load(f, sr=16000)
        style = {"suppress": {"suppress_tokens": [-1] + numerals}, "prompt": {"initial_prompt": PROMPT},
                 "none": {}}[args.style]
        segs, _ = model.transcribe(wav, language="tr", beam_size=5, temperature=0.0,
                                   condition_on_previous_text=False, **style)
        out[os.path.splitext(os.path.basename(f))[0]] = " ".join(s.text.strip() for s in segs).strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asr", choices=["balbal", "whisper"])
    ap.add_argument("--model")
    ap.add_argument("--compute-type", default="float16", help="whisper: float16 or float32")
    ap.add_argument("--style", choices=["prompt", "suppress", "none"], default="prompt", help="whisper: see the docstring")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(args.audio, "*.wav")))
    out = (balbal if args.asr == "balbal" else whisper)(files, args)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(len(out), "transcripts ->", args.out)


if __name__ == "__main__":
    main()
