#!/usr/bin/env python3
"""Build the non-speech test set: telephone-band (8 kHz, 300-3400 Hz, mu-law) clips with what a correct ASR should write.

  python nonspeech/make_set.py --datasets <dir> --out nonspeech/audio

<dir> holds the two datasets, unzipped (neither is redistributed here):
  vocalsound/  VocalSound 16 kHz, CC BY-SA 4.0: https://github.com/YuanGongND/vocalsound (vs_release_16k.zip)
  esc50/       ESC-50, CC BY-NC 3.0: https://github.com/karolpiczak/ESC-50 (master.zip)
Clip selection is seeded, so the same ids as nonspeech/clips.json come out.

Groups (all clips peak-normalised to 0.5 so level does not drive the result):
  vocal/<class>   VocalSound: cough, sigh, throat clearing, sniff, sneeze, laughter; one clip per speaker, 30 per class
  env/<class>     ESC-50: breathing, keyboard, door knock, footsteps, ... 10 per class
  silence/        digital silence and a low noise floor, 3-15 s
  ctrl/           real answers ("evet", "hayır", "tamam", ...) alone and after a cough, from Google Cloud TTS voices
                  (needs application default credentials); these MUST be transcribed
Writes <out>/<id>.wav and <out>/_meta.json {id: {group, cls, expect}} (the same as nonspeech/clips.json), where expect
is "" (nothing) or the words.
"""
import argparse
import csv
import glob
import json
import os
import random

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 8000
VOCAL = ["cough", "sigh", "throatclearing", "sniff", "sneeze", "laughter"]
ESC = ["breathing", "coughing", "sneezing", "snoring", "keyboard_typing", "mouse_click", "door_wood_knock",
       "footsteps", "clock_tick", "drinking_sipping", "door_wood_creaks", "can_opening", "pouring_water",
       "vacuum_cleaner", "washing_machine", "dog", "crying_baby", "car_horn", "siren", "engine", "rain", "wind"]
CTRL_TEXT = {"evet": "Evet.", "hayir": "Hayır.", "tamam": "Tamam.", "olur": "Olur.", "evet-onay": "Evet, onaylıyorum.",
             "bir-saniye": "Bir saniye."}
CTRL_VOICES = ["tr-TR-Standard-A", "tr-TR-Standard-B", "tr-TR-Wavenet-C", "tr-TR-Wavenet-E"]
SOS = butter(4, [300, 3400], btype="band", fs=SR, output="sos")


def mulaw(x, mu=255):
    x = np.clip(x, -1, 1)
    q = np.round((np.sign(x) * np.log1p(mu * np.abs(x)) / np.log1p(mu) + 1) / 2 * mu)
    y = q / mu * 2 - 1
    return np.sign(y) * ((1 + mu) ** np.abs(y) - 1) / mu


def phone(y, sr):
    y = librosa.resample(np.asarray(y, dtype=np.float32), orig_sr=sr, target_sr=SR) if sr != SR else y
    y = sosfilt(SOS, y)
    p = np.max(np.abs(y))
    if p > 0:
        y = y / p * 0.5
    return mulaw(y).astype(np.float32)


def load(path):
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    return y.mean(axis=1), sr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-vocal", type=int, default=30)
    ap.add_argument("--per-esc", type=int, default=10)
    args = ap.parse_args()
    rng = random.Random(0)
    os.makedirs(args.out, exist_ok=True)
    meta = {}

    def put(cid, y, group, cls, expect):
        sf.write(os.path.join(args.out, cid + ".wav"), y, SR, subtype="PCM_16")
        meta[cid] = {"group": group, "cls": cls, "expect": expect}

    # VocalSound: one clip per speaker per class, speakers drawn at random, balanced by gender where possible
    vs = [p for p in glob.glob(os.path.join(args.datasets, "vocalsound", "**", "audio_16k", "*.wav"), recursive=True)
          if "__MACOSX" not in p and not os.path.basename(p).startswith("._")]
    by_cls = {c: sorted(p for p in vs if p.endswith(f"_{c}.wav")) for c in VOCAL}
    coughs = []
    for c in VOCAL:
        files = by_cls[c][:]
        rng.shuffle(files)
        f = [p for p in files if os.path.basename(p).startswith("f")][: args.per_vocal // 2]
        m = [p for p in files if os.path.basename(p).startswith("m")][: args.per_vocal - len(f)]
        for p in f + m:
            y, sr = load(p)
            put(f"vocal-{c}-{os.path.basename(p)[:5]}", phone(y, sr), "vocal", c, "")
        if c == "cough":
            used = set(f + m)
            coughs = [p for p in files if p not in used][:8]  # unused speakers, for cough + answer controls

    # ESC-50
    esc_root = glob.glob(os.path.join(args.datasets, "esc50", "**", "meta", "esc50.csv"), recursive=True)[0]
    audio_dir = os.path.join(os.path.dirname(os.path.dirname(esc_root)), "audio")
    rows = list(csv.DictReader(open(esc_root, encoding="utf-8")))
    for c in ESC:
        files = sorted(r["filename"] for r in rows if r["category"] == c)
        rng.shuffle(files)
        for fn in files[: args.per_esc]:
            y, sr = load(os.path.join(audio_dir, fn))
            put(f"env-{c}-{fn[:-4]}", phone(y, sr), "env", c, "")

    # silence: digital zero and a quiet noise floor (about -60 dBFS), several lengths
    nrng = np.random.default_rng(0)
    for secs in (3, 5, 8, 10, 12, 15):
        put(f"silence-zero-{secs:02d}s", np.zeros(SR * secs, np.float32), "silence", "zero", "")
        put(f"silence-floor-{secs:02d}s", mulaw(sosfilt(SOS, nrng.normal(0, 0.001, SR * secs))).astype(np.float32),
            "silence", "floor", "")

    # controls: real short answers from Google TTS voices, alone and 0.6 s after a cough
    from google.cloud import texttospeech as tts
    client = tts.TextToSpeechClient()
    cfg = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16, sample_rate_hertz=24000)
    n = 0
    for vname in CTRL_VOICES:
        voice = tts.VoiceSelectionParams(language_code="tr-TR", name=vname)
        for key, text in CTRL_TEXT.items():
            wav = client.synthesize_speech(input=tts.SynthesisInput(text=text), voice=voice, audio_config=cfg)
            y = np.frombuffer(wav.audio_content[44:], dtype=np.int16).astype(np.float32) / 32768
            lead = np.zeros(int(0.5 * 24000), np.float32)
            words = text.lower().strip(".").replace(",", "")
            put(f"ctrl-{key}-{vname[6:].lower()}", phone(np.concatenate([lead, y, lead]), 24000), "ctrl", key, words)
            if key in ("evet", "hayir", "tamam") and n < len(coughs):
                c, csr = load(coughs[n])
                c = librosa.resample(c, orig_sr=csr, target_sr=24000)
                c = c / (np.max(np.abs(c)) + 1e-9) * np.max(np.abs(y))
                mix = np.concatenate([lead, c, np.zeros(int(0.6 * 24000), np.float32), y, lead])
                put(f"ctrl-cough+{key}-{vname[6:].lower()}", phone(mix, 24000), "ctrl", "cough+" + key, words)
                n += 1

    json.dump(meta, open(os.path.join(args.out, "_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(meta), "clips:", dict(Counter(m["group"] for m in meta.values())))


if __name__ == "__main__":
    main()
