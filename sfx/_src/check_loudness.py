"""Measure every finished file against the loudness caps (README "音量の基準").

Usage: python3 check_loudness.py   (from sfx/_src)
"""
import glob
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

from master import loudness_stats, lufs, true_peak_db, CAP_MOMENTARY, CAP_SHORT_TERM, LOOP_TARGET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def decode(path):
    with tempfile.TemporaryDirectory() as td:
        w = os.path.join(td, 'a.wav')
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ar', '48000', w], check=True)
        y, _ = sf.read(w, always_2d=True)
    return y


def main():
    bad = 0
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, '0*', '*.mp3'))):
        base = p[:-4]
        loop = os.path.exists(base + '.ogg')
        y = decode(base + '.ogg' if loop else p)
        m, s = loudness_stats(y, loop)
        tp = true_peak_db(y)
        L = lufs(y)
        # 0.5 dB of slack for the lossy encoder
        ok = tp <= -0.5 and (m <= CAP_MOMENTARY + 0.5 and s <= CAP_SHORT_TERM + 0.5)
        if loop:
            ok = ok and L <= LOOP_TARGET + 0.5
        bad += not ok
        rows.append((os.path.relpath(p, ROOT), m, s, L, tp, loop, ok))
    for r, m, s, L, tp, loop, ok in rows:
        print(f"{'OK ' if ok else 'NG '}{r:40s} M {m:6.1f}  S {s:6.1f}  I {L:6.1f}  TP {tp:5.1f}{'  loop' if loop else ''}")
    print(f'\n{len(rows)} files, {bad} over the caps')
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
