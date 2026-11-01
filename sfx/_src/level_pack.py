"""Pack-wide loudness check and levelling (2026-11-01).

Every sound in the pack is measured by its loudest moment (max momentary loudness, the
EBU R128 400 ms window), which is what the ear hears as "how loud did that get". Then:
  - effects (01..06): the loudest moment of every file is kept between EFFECT_MIN and EFFECT_MAX
  - loops (07): integrated loudness to BED_LUFS; radio (08): to RADIO_LUFS
  - true peak never above -1 dBTP (a lookahead limiter catches it if a raise would clip)
so no single sound jumps out of the VTT at the players.

  python level_pack.py          # report only
  python level_pack.py --apply  # rewrite the MP3/OGG files in place
"""
import os
import subprocess
import sys
import tempfile
import warnings

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

warnings.filterwarnings('ignore')
from dsp import limiter  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EFFECT_MAX = -12.0   # LUFS: the loudest 400 ms of any effect is never above this ...
EFFECT_MIN = -16.0   # ... nor below this, so small sounds stay smaller than explosions, but only by up to 4 dB
BED_LUFS = -22.0     # LUFS integrated, loops (they sit under voice chat)
RADIO_LUFS = -20.0   # LUFS integrated, radio shows (meant to be listened to)
CEIL = -1.0          # dBTP


def decode(path):
    with tempfile.TemporaryDirectory() as td:
        w = os.path.join(td, 'x.wav')
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ar', '48000', '-ac', '2', w], check=True)
        y, sr = sf.read(w, always_2d=True)
    return y, sr


def max_momentary(y, sr):
    """Loudest 400 ms (K-weighted), stepped every 100 ms."""
    meter = pyln.Meter(sr, block_size=0.4)
    k = meter._filters  # K-weighting filters from pyloudnorm
    z = y.copy()
    for f in k.values():
        for ch in range(z.shape[1]):
            z[:, ch] = f.apply_filter(z[:, ch])
    win, hop = int(0.4 * sr), int(0.1 * sr)
    if len(z) < win:
        z = np.concatenate([z, np.zeros((win - len(z), z.shape[1]))])
    best = -120.0
    for i in range(0, len(z) - win + 1, hop):
        p = np.mean(np.sum(z[i:i + win] ** 2, axis=1) / 1.0)
        if p > 0:
            best = max(best, -0.691 + 10 * np.log10(p))
    return best


def true_peak(y):
    up = signal.resample_poly(y, 4, 1, axis=0)
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


def integrated(y, sr):
    try:
        return pyln.Meter(sr).integrated_loudness(y)
    except ValueError:
        return float('nan')


def files():
    for d in sorted(os.listdir(ROOT)):
        if d[:2].isdigit() and os.path.isdir(os.path.join(ROOT, d)):
            for f in sorted(os.listdir(os.path.join(ROOT, d))):
                if f.endswith('.mp3'):
                    yield d, f


def encode(y, sr, mp3, ogg):
    with tempfile.TemporaryDirectory() as td:
        w = os.path.join(td, 'x.wav')
        sf.write(w, y, sr, subtype='PCM_24')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', w, '-c:a', 'libmp3lame', '-q:a', '1', mp3], check=True)
        if ogg:
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', w, '-c:a', 'libvorbis', '-q:a', '6', ogg], check=True)


def main(apply):
    rows = []
    for d, f in files():
        mp3 = os.path.join(ROOT, d, f)
        ogg = mp3[:-4] + '.ogg'
        has_ogg = os.path.exists(ogg)
        # loops are levelled from the OGG (the better copy) when there is one
        y, sr = decode(ogg if has_ogg else mp3)
        bed = d.startswith('07') or d.startswith('08')
        mm, il, tp = max_momentary(y, sr), integrated(y, sr), true_peak(y)
        if d.startswith('08'):
            gain = RADIO_LUFS - il
        elif bed:
            gain = BED_LUFS - il
        else:
            gain = EFFECT_MAX - mm if mm > EFFECT_MAX else (EFFECT_MIN - mm if mm < EFFECT_MIN else 0.0)
        new_tp = tp + gain
        rows.append((d, f[:-4], mm, il, tp, gain))
        # under 0.5 dB is MP3 decode drift: leave the file alone rather than re-encode it again
        if apply and abs(gain) > 0.5:
            # short transients (single shots) lose level to the limiter, so iterate on the measured value
            z = y
            for _ in range(12):
                z = z * 10 ** (gain / 20)
                if true_peak(z) > CEIL:
                    z = limiter(z, CEIL - 0.4)
                    t2 = true_peak(z)
                    if t2 > CEIL:
                        z *= 10 ** ((CEIL - t2) / 20)
                if d.startswith('08'):
                    gain = RADIO_LUFS - integrated(z, sr)
                elif bed:
                    gain = BED_LUFS - integrated(z, sr)
                else:
                    m2 = max_momentary(z, sr)
                    gain = EFFECT_MAX - m2 if m2 > EFFECT_MAX else (EFFECT_MIN - m2 if m2 < EFFECT_MIN else 0.0)
                if abs(gain) < 0.3:
                    break
            encode(z, sr, mp3, ogg if has_ogg else None)
    print(f"{'file':44s} {'maxM':>6s} {'int':>6s} {'TP':>6s} {'gain':>6s}")
    for d, n, mm, il, tp, gain in rows:
        print(f"{(d[3:] + '/' + n)[:44]:44s} {mm:6.1f} {il:6.1f} {tp:6.1f} {gain:+6.1f}")
    fx = [r[2] for r in rows if not r[0].startswith(('07', '08'))]
    print(f"\neffects: loudest moment ranges {min(fx):.1f} .. {max(fx):.1f} LUFS (spread {max(fx) - min(fx):.1f} dB) "
          f"-> kept within {EFFECT_MIN} .. {EFFECT_MAX}")


if __name__ == '__main__':
    main('--apply' in sys.argv)
