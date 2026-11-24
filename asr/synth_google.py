#!/usr/bin/env python3
"""Synthesize the reference reading of every line with Google Cloud Text-to-Speech, 8 kHz telephone band.

Credentials come from Application Default Credentials (gcloud auth application-default login); nothing is read
from or written to this repo. The TTS gets the reading already spelled out, so its own normalizer plays no part.

  python asr/synth_google.py --voice tr-TR-Wavenet-E --out audio/google-wavenet-e
"""
import argparse
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data", "tr_customer_lines.jsonl")
PHONE_SR = 8000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import librosa
    import soundfile as sf
    from google.cloud import texttospeech as tts

    client = tts.TextToSpeechClient()
    voice = tts.VoiceSelectionParams(language_code="tr-TR", name=args.voice)
    config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16, sample_rate_hertz=24000)
    os.makedirs(args.out, exist_ok=True)
    with open(DATA, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]
    for item in items:
        path = os.path.join(args.out, item["id"] + ".wav")
        if os.path.exists(path):
            continue
        resp = client.synthesize_speech(input=tts.SynthesisInput(text=item["spoken"][0]), voice=voice,
                                        audio_config=config)
        wav, sr = sf.read(io.BytesIO(resp.audio_content), dtype="float32")
        sf.write(path, librosa.resample(wav, orig_sr=sr, target_sr=PHONE_SR), PHONE_SR)
    print(args.voice, len(items), "lines ->", args.out)


if __name__ == "__main__":
    main()
