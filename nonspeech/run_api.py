#!/usr/bin/env python3
"""Transcribe the clip folder with a cloud STT, directly or behind a Silero VAD gate, and write {id: text} JSON.

  python nonspeech/run_api.py --engine elevenlabs --audio nonspeech/audio --out nonspeech/results/elevenlabs-scribe-v2.json
  python nonspeech/run_api.py --engine google:chirp_3@us --audio ... --out ...
  python nonspeech/run_api.py --engine elevenlabs --vad 0.3 --audio ... --out ...

elevenlabs: Scribe v2, language "tur", audio-event tags on (the scorer drops tags such as "[öksürük]").
google:<model>[@<location>]: Speech-to-Text v2, tr-TR, recognizer "_" in GOOGLE_CLOUD_PROJECT, application default
credentials. Models used here: chirp_3@us, chirp_2@us-central1, long (global).
--vad T: only the speech Silero VAD finds at threshold T is sent, packed into chunks under 9 s that end in a pause;
a clip with no speech gets "" without a request.
Keys come from the environment (ELEVENLABS_API_KEY) or a .env in the working directory; nothing is printed.
Already transcribed ids in --out are skipped, so a run can be resumed.
"""
import argparse
import glob
import io
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import librosa
import requests
import soundfile as sf
from dotenv import load_dotenv

load_dotenv()
MAX_CHUNK_S = 9.0
MAX_GAP_S = 1.5


def wav_bytes(y, sr):
    b = io.BytesIO()
    sf.write(b, y, sr, format="WAV", subtype="PCM_16")
    return b.getvalue()


def elevenlabs(y, sr):
    for i in range(5):
        r = requests.post("https://api.elevenlabs.io/v1/speech-to-text",
                          headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                          files={"file": ("a.wav", wav_bytes(y, sr), "audio/wav")},
                          data={"model_id": "scribe_v2", "language_code": "tur", "tag_audio_events": "true"},
                          timeout=120)
        if r.status_code in (429, 500, 502, 503, 504) and i < 4:
            time.sleep(2 ** i)
            continue
        r.raise_for_status()
        return r.json().get("text", "")


def google(spec):
    from google.api_core import exceptions, retry
    from google.api_core.client_options import ClientOptions
    from google.cloud.speech_v2 import SpeechClient
    from google.cloud.speech_v2.types import cloud_speech as cs

    model, _, loc = spec.partition("@")
    loc = loc or "global"
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    client = SpeechClient(client_options=ClientOptions(api_endpoint=f"{loc}-speech.googleapis.com")
                          if loc != "global" else None)
    cfg = cs.RecognitionConfig(auto_decoding_config=cs.AutoDetectDecodingConfig(), language_codes=["tr-TR"],
                               model=model)
    again = retry.Retry(predicate=retry.if_exception_type(exceptions.ResourceExhausted,
                                                          exceptions.ServiceUnavailable), timeout=300)

    def run(y, sr):
        req = cs.RecognizeRequest(recognizer=f"projects/{project}/locations/{loc}/recognizers/_", config=cfg,
                                  content=wav_bytes(y, sr))
        resp = client.recognize(request=req, retry=again)
        return " ".join(r.alternatives[0].transcript for r in resp.results if r.alternatives).strip()
    return run


def vad_gate(engine, threshold):
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    opts = VadOptions(threshold=threshold, min_silence_duration_ms=300, speech_pad_ms=250,
                      max_speech_duration_s=MAX_CHUNK_S)

    def run(y, sr):
        y16 = librosa.resample(y, orig_sr=sr, target_sr=16000) if sr != 16000 else y
        chunks = []
        for t in get_speech_timestamps(y16, opts):
            s, e = t["start"] / 16000, t["end"] / 16000
            if chunks and s - chunks[-1][1] <= MAX_GAP_S and e - chunks[-1][0] <= MAX_CHUNK_S:
                chunks[-1][1] = e
            else:
                chunks.append([s, e])
        parts = [engine(y[int(s * sr): int(e * sr)], sr).strip() for s, e in chunks]
        return " ".join(p for p in parts if p)
    return run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True, help="elevenlabs or google:<model>[@<location>]")
    ap.add_argument("--vad", type=float, help="gate with Silero VAD at this threshold (e.g. 0.3)")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    eng = elevenlabs if args.engine == "elevenlabs" else google(args.engine.split(":", 1)[1])
    if args.vad is not None:
        eng = vad_gate(eng, args.vad)
    out = json.load(open(args.out, encoding="utf-8")) if os.path.exists(args.out) else {}
    todo = [p for p in sorted(glob.glob(os.path.join(args.audio, "*.wav")))
            if os.path.splitext(os.path.basename(p))[0] not in out]

    def one(p):
        y, sr = sf.read(p, dtype="float32")
        return os.path.splitext(os.path.basename(p))[0], eng(y, sr)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with ThreadPoolExecutor(args.workers) as ex:
        for k, t in ex.map(one, todo):
            out[k] = t
    json.dump(dict(sorted(out.items())), open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{args.engine}{f' +vad {args.vad}' if args.vad is not None else ''}: {len(out)} clips -> {args.out}")


if __name__ == "__main__":
    main()
