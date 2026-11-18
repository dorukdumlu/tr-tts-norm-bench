"""One function per normalizer: a list of input lines in, a list of output lines out.

Each adapter calls the library's documented top-level entry point with its default options, except where a
second row says otherwise. Versions are recorded by run.py.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def normalizer_tr(lines, policy="preserve"):
    from normalizer_tr import Normalizer

    n = Normalizer()
    return [n.normalize(t, ambiguity_policy=policy).normalized_text for t in lines]


def normalizer_tr_fallback(lines):
    return normalizer_tr(lines, policy="fallback")


def turkificate(lines):
    import turkificate as tk

    return [tk.turkificate(t) for t in lines]


def turkce_normalize(lines):
    from turkce_normalize import normalize

    return [normalize(t) for t in lines]


def trnorm(lines):
    import trnorm as tn

    return [tn.normalize(t) for t in lines]


def trnorm_js(lines):
    script = os.path.join(ROOT, "js", "run.mjs")
    proc = subprocess.run(["node", script], input=json.dumps(lines), capture_output=True, text=True,
                          encoding="utf-8", cwd=os.path.join(ROOT, "js"), check=True)
    return json.loads(proc.stdout)


def freyatts_main(lines):
    sys.path.insert(0, HERE)
    from freyatts_main import normalize

    return [normalize(t) for t in lines]


ADAPTERS = {
    "normalizer-tr": normalizer_tr,
    "normalizer-tr (fallback)": normalizer_tr_fallback,
    "trnorm-js": trnorm_js,
    "turkce-normalize": turkce_normalize,
    "turkificate": turkificate,
    "trnorm (ASR)": trnorm,
    "FreyaTTS main": freyatts_main,
}


def versions():
    from importlib.metadata import version

    out = {}
    for name, pkg in [("normalizer-tr", "normalizer-tr"), ("turkce-normalize", "turkce-normalize"),
                      ("turkificate", "turkificate"), ("trnorm (ASR)", "trnorm")]:
        out[name] = version(pkg)
    out["normalizer-tr (fallback)"] = out["normalizer-tr"]
    with open(os.path.join(ROOT, "js", "node_modules", "@ozgurguler", "trnorm", "package.json"),
              encoding="utf-8") as f:
        out["trnorm-js"] = json.load(f)["version"]
    out["FreyaTTS main"] = "146d36c"
    return out
