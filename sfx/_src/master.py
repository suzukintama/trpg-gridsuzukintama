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


def finish(x, target_lufs=-16.0, ceiling=-1.0, loop=False, fin=0.0005, fout=0.03, drive=None, max_gr=3.0):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    if loop:
        # filter circularly so the loop seam carries the right filter state
        n = len(x)
        x = hp(np.concatenate([x, x]) - np.mean(x, axis=0), 22, 2)[n:]
    else:
        x = hp(x - np.mean(x, axis=0), 22, 2)
    if not loop:
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
    rec = dict(name=rel_name, dur=len(y) / SR, lufs=lufs(y), tp=true_peak_db(y),
               gr=max(0.0, pre_peak - (-1.4)), loop=loop, note=note)
    REPORT.append(rec)
    print(f"{rel_name:34s} {rec['dur']:6.2f}s  {rec['lufs']:6.1f} LUFS  TP {rec['tp']:5.1f}  limGR~{rec['gr']:4.1f}dB")
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
