"""Mastering + export (WAV master -> MP3 / OGG) and QA helpers."""
import os
import warnings
warnings.filterwarnings("ignore")
import subprocess
import tempfile

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

from dsp import SR, hp, limiter, fade, ns

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPORT = []


def lufs(x):
    m = pyln.Meter(SR, block_size=0.1 if len(x) < SR * 0.6 else 0.4)
    try:
        return m.integrated_loudness(x)
    except ValueError:
        return float('nan')


def true_peak_db(x):
    up = signal.resample_poly(x, 4, 1, axis=0)
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


# ---- hearing-safe loudness caps (see README "音量の基準") ----
# EBU R128 / R128 s1 (short-form): true peak <= -1 dBTP, short-term (3 s) <= -18 LUFS.
# Our own extra cap for impulsive sounds: momentary (0.4 s) <= -14 LUFS.
# Ambience loops are set to -23 LUFS integrated (EBU R128).
CAP_SHORT_TERM = -18.0
CAP_MOMENTARY = -14.0
LOOP_TARGET = -23.0

_KW = [([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]),
       ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])]   # BS.1770 K-weighting @48 kHz


def loudness_stats(x, loop=False):
    """(max momentary, max short-term) loudness in LUFS (BS.1770 K-weighting, R128 windows)."""
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    if loop:
        x = np.concatenate([x, x[:ns(3.0)]])          # windows may wrap round a loop
    else:
        x = np.concatenate([x, np.zeros((ns(3.0), 2))])
    y = x
    for b, a in _KW:
        y = signal.lfilter(b, a, y, axis=0)
    p = np.sum(y ** 2, axis=1)
    c = np.concatenate([[0.0], np.cumsum(p)])
    def mx(win):
        w = ns(win)
        if len(p) <= w:
            return -0.691 + 10 * np.log10(c[-1] / w + 1e-20)
        hop = ns(0.1)
        idx = np.arange(0, len(p) - w, hop)
        ms = (c[idx + w] - c[idx]) / w
        return -0.691 + 10 * np.log10(np.max(ms) + 1e-20)
    return mx(0.4), mx(3.0)


def finish(x, target_lufs=-16.0, ceiling=-1.2, loop=False, fin=0.0005, fout=0.03, drive=None, max_gr=3.0):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    if loop:
        # filter circularly so the loop seam carries the right filter state
        n = len(x)
        x = hp(np.concatenate([x, x]) - np.mean(x, axis=0), 22, 2)[n:]
    else:
        x = hp(x - np.mean(x, axis=0), 22, 2)
    if not loop:
        # drop leading silence so the sound starts the moment it is triggered
        env = np.max(np.abs(x), axis=1)
        above = np.nonzero(env > np.max(env) * 10 ** (-50 / 20))[0]
        if len(above):
            x = x[max(0, above[0] - ns(0.004)):]
        x = fade(x, fin, fout)
    # trim trailing near-silence (keeps natural tails, drops digital zeros)
    if not loop:
        env = np.max(np.abs(x), axis=1)
        thr = np.max(env) * 10 ** (-72 / 20)
        last = np.nonzero(env > thr)[0]
        if len(last):
            x = x[:min(len(x), last[-1] + ns(0.02))]
            x = fade(x, 0, min(0.05, len(x) / SR / 4))
    if drive is not None:
        # impulsive material: push the peak `drive` dB into the limiter
        x = x * 10 ** ((ceiling - 0.4 + drive) / 20) / (np.max(np.abs(x)) + 1e-12)
    else:
        L = lufs(x)
        if np.isfinite(L):
            x = x * 10 ** ((target_lufs - L) / 20)
        # never squash sparse transients more than max_gr dB to chase loudness
        pk = 20 * np.log10(np.max(np.abs(x)) + 1e-12)
        if pk > ceiling - 0.4 + max_gr:
            x = x * 10 ** ((ceiling - 0.4 + max_gr - pk) / 20)
    pre_peak = 20 * np.log10(np.max(np.abs(x)) + 1e-12)
    # limit at slightly under ceiling and leave room for inter-sample peaks
    x = limiter(x, ceiling - 0.4)
    tp = true_peak_db(x)
    if tp > ceiling:
        x *= 10 ** ((ceiling - tp) / 20)
    if loop:
        L = lufs(x)
        if np.isfinite(L) and L > LOOP_TARGET:
            x = x * 10 ** ((LOOP_TARGET - L) / 20)
    # hearing-safe caps: only ever turn down
    m, st_ = loudness_stats(x, loop)
    over = max(m - CAP_MOMENTARY, st_ - CAP_SHORT_TERM, 0.0)
    if over > 0:
        x = x * 10 ** (-over / 20)
    return x, pre_peak


def export(rel_name, x, target_lufs=-16.0, loop=False, ogg=False, note='', drive=None, max_gr=3.0):
    """rel_name like '01_銃/拳銃_単発' (no extension)."""
    y, pre_peak = finish(x, target_lufs, loop=loop, drive=drive, max_gr=max_gr)
    path = os.path.join(ROOT, rel_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, 'm.wav')
        sf.write(wav, y, SR, subtype='PCM_24')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-c:a', 'libmp3lame',
                        '-q:a', '1', path + '.mp3'], check=True)
        if ogg:
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-c:a', 'libvorbis',
                            '-q:a', '6', path + '.ogg'], check=True)
        keep = os.environ.get('SFX_KEEP_WAV')
        if keep:
            os.makedirs(keep, exist_ok=True)
            import shutil
            shutil.copy(wav, os.path.join(keep, rel_name.replace('/', '__') + '.wav'))
    mm, ss = loudness_stats(y, loop)
    rec = dict(name=rel_name, dur=len(y) / SR, lufs=lufs(y), tp=true_peak_db(y),
               gr=max(0.0, pre_peak - (-1.4)), loop=loop, note=note, mom=mm, st=ss)
    REPORT.append(rec)
    print(f"{rel_name:34s} {rec['dur']:6.2f}s  {rec['lufs']:6.1f} LUFS  M {mm:6.1f}  S {ss:6.1f}  TP {rec['tp']:5.1f}")
    qa_dir = os.environ.get('SFX_QA')
    if qa_dir:
        spectro(y, os.path.join(qa_dir, rel_name.replace('/', '__') + '.png'), rel_name)
    return y


def spectro(y, out, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    os.makedirs(os.path.dirname(out), exist_ok=True)
    m = y.mean(axis=1)
    fig, ax = plt.subplots(2, 1, figsize=(10, 5.5), gridspec_kw={'height_ratios': [1, 2]})
    t = np.arange(len(m)) / SR
    ax[0].plot(t, y[:, 0], lw=0.4, color='c')
    ax[0].plot(t, y[:, 1], lw=0.4, color='m', alpha=0.6)
    ax[0].set_xlim(0, t[-1])
    ax[0].set_ylim(-1, 1)
    ax[0].set_title(title, fontsize=9)
    f, tt, S = signal.spectrogram(m, SR, nperseg=1024, noverlap=896)
    ax[1].pcolormesh(tt, f, 10 * np.log10(S + 1e-14), shading='auto', vmin=-130, vmax=-30, cmap='magma')
    ax[1].set_yscale('symlog', linthresh=500)
    ax[1].set_ylim(30, 22000)
    fig.tight_layout()
    fig.savefig(out, dpi=70)
    plt.close(fig)
