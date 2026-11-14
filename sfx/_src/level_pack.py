"""Pack-wide loudness caps (hearing-safe), applied to every finished file.

Same caps as the mastering stage (master.py, README "音量の基準"):
  - every file: true peak <= -1 dBTP
  - effects (01..06, 09..11 one-shots): max momentary (0.4 s) <= -14 LUFS and max short-term (3 s) <= -18 LUFS
    (EBU R128 s1 short-form limit, plus our own momentary cap for impulsive sounds)
  - loops (anything with an .ogg twin) and radio (08): integrated <= -23 LUFS (EBU R128);
    per-file quieter targets in OVERRIDE are kept as they are
Files are only ever turned DOWN; anything already under the caps is left untouched (no re-encode).

  python level_pack.py          # report only
  python level_pack.py --apply  # rewrite the MP3/OGG files that are over a cap
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
from master import loudness_stats, CAP_MOMENTARY, CAP_SHORT_TERM, LOOP_TARGET  # noqa: E402

CEIL = -1.0          # dBTP
SLACK = 0.5          # dB of measurement / MP3 drift tolerated before a file is touched
# per-file integrated targets that override BED_LUFS (2026-11-02 GM: the bar was too loud)
OVERRIDE = {'下層のバー': -25.0, '下層のバー_曲だけ': -25.0,
            # the live-house crowds are a wall of noise, kept a little under the other loops (LIVE_LUFS);
            # the thin ones lower still, so a near-empty room really sounds near empty
            'ライブハウス_終演後のざわめき': -25.0, 'ライブハウス_客入り2_まばら': -25.0,
            'ライブハウス_出待ちのファン': -25.0,
            'ライブハウス_客入り1_ほぼ空': -27.0, 'ライブハウス_演奏前の静けさ': -27.0,
            # role loops (2026-11-03): rooms and radio that sit under talk, the patient monitor lowest of all
            'テック_工房': -24.0, 'メドテック_診療所': -24.0, 'エグゼク_高層オフィス': -24.0, 'ローマン_警察無線': -24.0,
            'ノーマッド_荒野の風': -24.0, 'ノーマッド_焚き火': -24.0, 'メディア_記者会見': -24.0,
            'メドテック_生体モニター': -27.0}
LIVE_LUFS = -24.0


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


def caps_gain(y, sr, d, name, loop):
    """dB to turn the file down by (<= 0) so that it meets every cap."""
    m, st_ = loudness_stats(y, loop)
    tp = true_peak(y)
    g = min(0.0, CEIL - tp)
    if loop or d.startswith('08'):
        il = integrated(y, sr)
        target = min(LOOP_TARGET, OVERRIDE.get(name, LOOP_TARGET))
        if il == il:   # not NaN
            g = min(g, target - il)
    else:
        g = min(g, CAP_MOMENTARY - m, CAP_SHORT_TERM - st_)
    return g, m, st_, tp


def main(apply):
    rows = []
    changed = 0
    for d, f in files():
        mp3 = os.path.join(ROOT, d, f)
        ogg = mp3[:-4] + '.ogg'
        has_ogg = os.path.exists(ogg)
        y, sr = decode(ogg if has_ogg else mp3)
        g, m, st_, tp = caps_gain(y, sr, d, f[:-4], has_ogg)
        rows.append((d, f[:-4], m, st_, tp, g))
        # loudness gets 0.5 dB of slack for MP3 drift; the true-peak ceiling gets none
        if apply and (g < -SLACK or tp > CEIL):
            z = y * 10 ** ((min(g, CEIL - 0.3 - tp) - 0.2) / 20)
            encode(z, sr, mp3, ogg if has_ogg else None)
            changed += 1
    print(f"{'file':44s} {'maxM':>6s} {'maxS':>6s} {'TP':>6s} {'gain':>6s}")
    for d, n, m, st_, tp, g in rows:
        print(f"{(d[3:] + '/' + n)[:44]:44s} {m:6.1f} {st_:6.1f} {tp:6.1f} {g:+6.1f}")
    print(f"\n{len(rows)} files; {sum(1 for r in rows if r[5] < -SLACK)} over a cap"
          + (f"; {changed} turned down" if apply else ""))


if __name__ == '__main__':
    main('--apply' in sys.argv)
