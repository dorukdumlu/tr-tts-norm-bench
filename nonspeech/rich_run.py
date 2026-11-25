#!/usr/bin/env python3
"""Transcribe keeping word confidences: {id: {"text": str, "words": [[word, conf]], "conf": utterance conf or None}}.

  python nonspeech/rich_run.py --engine elevenlabs|google:<model>@<loc> --audio nonspeech/audio --out <json>
elevenlabs: exp(word logprob). google: word confidence (not offered by chirp_3) and utterance confidence.
"""
import argparse
import glob
import io
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests
import soundfile as sf
from dotenv import dotenv_values

ENV = {**dotenv_values(".env"), **os.environ}


def post(url, **kw):
    for i in range(6):
        r = requests.post(url, timeout=120, **kw)
        if r.status_code in (429, 500, 502, 503, 504) and i < 5:
            time.sleep(2 ** i)
            continue
        r.raise_for_status()
        return r.json()


def eleven(path):
    d = post("https://api.elevenlabs.io/v1/speech-to-text", headers={"xi-api-key": ENV["ELEVENLABS_API_KEY"]},
             files={"file": open(path, "rb")},
             data={"model_id": "scribe_v2", "language_code": "tur", "tag_audio_events": "true"})
    ws = [[w["text"], math.exp(w["logprob"]) if w.get("logprob") is not None else None]
          for w in d.get("words", []) if w.get("type") == "word"]
    return {"text": d.get("text", ""), "words": ws, "conf": None}


def google_factory(spec):
    from google.api_core import exceptions, retry
    from google.api_core.client_options import ClientOptions
    from google.cloud.speech_v2 import SpeechClient
    from google.cloud.speech_v2.types import cloud_speech as cs
    model, _, loc = spec.partition("@")
    loc = loc or "global"
    project = ENV["GOOGLE_CLOUD_PROJECT"]
    client = SpeechClient(client_options=ClientOptions(api_endpoint=f"{loc}-speech.googleapis.com")
                          if loc != "global" else None)
    cfg = cs.RecognitionConfig(auto_decoding_config=cs.AutoDetectDecodingConfig(), language_codes=["tr-TR"],
                               model=model, features=cs.RecognitionFeatures(enable_word_confidence=model != "chirp_3"))
    again = retry.Retry(predicate=retry.if_exception_type(exceptions.ResourceExhausted,
                                                          exceptions.ServiceUnavailable), timeout=600)

    def run(path):
        y, sr = sf.read(path, dtype="float32")
        b = io.BytesIO()
        sf.write(b, y, sr, format="WAV", subtype="PCM_16")
        resp = client.recognize(request=cs.RecognizeRequest(
            recognizer=f"projects/{project}/locations/{loc}/recognizers/_", config=cfg, content=b.getvalue()),
            retry=again)
        alts = [r.alternatives[0] for r in resp.results if r.alternatives]
        return {"text": " ".join(a.transcript for a in alts).strip(),
                "words": [[w.word, w.confidence] for a in alts for w in a.words],
                "conf": min((a.confidence for a in alts), default=None)}
    return run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    eng = {"elevenlabs": eleven}.get(args.engine) or google_factory(args.engine.split(":", 1)[1])
    out = json.load(open(args.out, encoding="utf-8")) if os.path.exists(args.out) else {}
    todo = [p for p in sorted(glob.glob(os.path.join(args.audio, "*.wav")))
            if os.path.splitext(os.path.basename(p))[0] not in out]

    def one(p):
        k = os.path.splitext(os.path.basename(p))[0]
        try:
            return k, eng(p)
        except Exception as e:
            return k, {"error": f"{type(e).__name__}: {str(e)[:200]}"}

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with ThreadPoolExecutor(args.workers) as ex:
        for k, v in ex.map(one, todo):
            out[k] = v
    json.dump(dict(sorted(out.items())), open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(args.engine, len(out), "clips,", sum("error" in v for v in out.values()), "errors ->", args.out)


if __name__ == "__main__":
    main()
