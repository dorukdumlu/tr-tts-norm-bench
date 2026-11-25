"""AudioSet sound-event classifier as a "was this speech?" gate in front of any ASR.

  python nonspeech/ast_gate.py --audio nonspeech/audio --out nonspeech/results/confidence/ast.json          # per clip: speech prob and top classes
  python nonspeech/ast_gate.py --eval nonspeech/clips.json nonspeech/results/confidence/ast.json nonspeech/results/<asr>.json ...

Speech probability = max sigmoid over AudioSet speech classes (Speech, Male/Female/Child speech, Conversation,
Narration). The clip is scored in 1 s windows with 0.5 s hop and the maximum is kept, so a short "evet" after a
long cough is not averaged away. A yes counts only when the ASR wrote a yes-word AND speech prob >= threshold.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

SPEECH = ["Speech", "Male speech, man speaking", "Female speech, woman speaking", "Child speech, kid speaking",
          "Conversation", "Narration, monologue"]
MODEL = "MIT/ast-finetuned-audioset-10-10-0.4593"


def classify(paths):
    import librosa
    import torch
    from transformers import ASTFeatureExtractor, ASTForAudioClassification
    fe = ASTFeatureExtractor.from_pretrained(MODEL)
    model = ASTForAudioClassification.from_pretrained(MODEL).eval().cuda()
    labels = model.config.id2label
    sp_ids = [i for i, l in labels.items() if l in SPEECH]
    out = {}
    for p in paths:
        y, _ = librosa.load(p, sr=16000)
        win, hop = 16000, 8000
        segs = [y[i:i + win] for i in range(0, max(1, len(y) - win + 1), hop)] or [y]
        if len(y) > win and (len(y) - win) % hop:
            segs.append(y[-win:])
        feats = fe(segs, sampling_rate=16000, return_tensors="pt")
        with torch.no_grad():
            pr = torch.sigmoid(model(feats["input_values"].cuda()).logits).cpu().numpy()
        sp = pr[:, sp_ids].max(axis=1)
        whole = pr.max(axis=0)
        top = [(labels[i], round(float(whole[i]), 3)) for i in np.argsort(-whole)[:3]]
        out[os.path.splitext(os.path.basename(p))[0]] = {"speech": round(float(sp.max()), 4), "top": top}
    return out


def evaluate(meta_path, ast_path, asr_paths):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gate_eval import YES_CTRL, wilson
    from score import bucket
    meta = json.load(open(meta_path, encoding="utf-8"))
    ast = json.load(open(ast_path, encoding="utf-8"))
    ns = [k for k, m in meta.items() if m["group"] != "ctrl"]
    yc = [k for k, m in meta.items() if m["group"] == "ctrl" and m["cls"] in YES_CTRL]
    print("| ASR | threshold | false yes | 95% CI | real yes kept |")
    print("|---|---|---|---|---|")
    for ap in asr_paths:
        res = json.load(open(ap, encoding="utf-8"))
        text = {k: (v["text"] if isinstance(v, dict) else v) for k, v in res.items()}
        for th in (None, 0.1, 0.2, 0.3, 0.5):
            ok = lambda k: bucket(text.get(k, "")) == "AFFIRM" and (th is None or ast[k]["speech"] >= th)
            n = [k for k in ns if k in text]
            f = sum(ok(k) for k in n)
            lo, hi = wilson(f, len(n))
            print(f"| {os.path.splitext(os.path.basename(ap))[0]} | {th or 'none'} | {f}/{len(n)} ({100*f/len(n):.1f}%) "
                  f"| {100*lo:.1f}-{100*hi:.1f}% | {sum(ok(k) for k in yc)}/{len(yc)} |")
    sp_ns = np.array([ast[k]["speech"] for k in ns])
    sp_yc = np.array([ast[k]["speech"] for k in yc])
    print(f"\nspeech prob: non-speech median {np.median(sp_ns):.3f}, 95th pct {np.percentile(sp_ns, 95):.3f}; "
          f"yes-controls min {sp_yc.min():.3f}, median {np.median(sp_yc):.3f}")
    for th in (0.1, 0.2, 0.3, 0.5):
        print(f"  >= {th}: non-speech passing {np.mean(sp_ns >= th)*100:.1f}%, yes-controls passing "
              f"{int((sp_yc >= th).sum())}/{len(sp_yc)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio")
    ap.add_argument("--out")
    ap.add_argument("--eval", nargs="+")
    a = ap.parse_args()
    if a.eval:
        evaluate(a.eval[0], a.eval[1], a.eval[2:])
        return
    res = classify(sorted(glob.glob(os.path.join(a.audio, "*.wav"))))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(res), "clips ->", a.out)


if __name__ == "__main__":
    main()
