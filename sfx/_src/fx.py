"""Sound-design tools that work on real recordings (no oscillators).

The idea is the classic film approach: start from a real sound, then change its
speed, smear it in time, borrow another recording's resonance, or cut it into
grains, so the result keeps the life of the recording but no longer sounds like
an everyday object.
All functions take/return stereo float arrays (n, 2) unless noted.
"""
import numpy as np
from scipy import signal

from dsp import SR, Gen, ns, lp, hp, bp


def st(y):
    return np.stack([y, y], 1) if y.ndim == 1 else y


def norm(y, peak=1.0):
    return y / (np.max(np.abs(y)) + 1e-12) * peak


def rms_norm(y, rms=0.1):
    return y / (np.sqrt(np.mean(y ** 2)) + 1e-12) * rms


def rate(y, r):
    """Play back r times faster (tape style: pitch and length change together)."""
    y = st(y)
    n = int(len(y) / r)
    idx = np.arange(n) * r
    return np.stack([np.interp(idx, np.arange(len(y)), y[:, c]) for c in range(2)], 1)


def varispeed(y, curve):
    """Play back with a speed curve (array of rates, one per output sample, or callable t->rate).

    curve e.g. falling to 0 gives a 'power down' / tape stop.
    """
    y = st(y)
    if callable(curve):
        n_out = len(y) * 4
        t = np.arange(n_out) / SR
        r = curve(t)
        stop = np.nonzero(r[1:] < 1e-3)[0]
        if len(stop):
            r = r[:stop[0] + 1]
    else:
        r = np.asarray(curve, dtype=float)
    pos = np.cumsum(r)
    pos = pos[pos < len(y) - 1]
    return np.stack([np.interp(pos, np.arange(len(y)), y[:, c]) for c in range(2)], 1)


def fade(y, fin=0.005, fout=0.05):
    y = y.copy()
    a, b = min(ns(fin), len(y) // 2), min(ns(fout), len(y) // 2)
    if a:
        y[:a] *= np.linspace(0, 1, a)[:, None]
    if b:
        y[-b:] *= (np.cos(np.linspace(0, np.pi / 2, b)) ** 2)[:, None]
    return y


def paulstretch(y, factor, win=0.25, seed=1):
    """Extreme time-stretch with phase randomisation (smooth, evolving texture)."""
    g = np.random.default_rng(seed)
    y = st(y)
    N = int(win * SR) // 2 * 2
    hop_out = N // 4
    hop_in = hop_out / factor
    w = np.hanning(N)
    n_frames = int((len(y) - N) / hop_in)
    out = np.zeros((n_frames * hop_out + N, 2))
    for i in range(max(n_frames, 0)):
        a = int(i * hop_in)
        for c in range(2):
            seg = y[a:a + N, c] * w
            mag = np.abs(np.fft.rfft(seg))
            ph = g.uniform(0, 2 * np.pi, len(mag))
            out[i * hop_out:i * hop_out + N, c] += np.fft.irfft(mag * np.exp(1j * ph), N) * w
    return out


def resonate(y, ir, wet=0.6, ir_len=None):
    """Give y the resonance of another recording (e.g. a struck metal plate) by convolution."""
    y = st(y)
    ir = st(ir)
    if ir_len:
        ir = ir[:ns(ir_len)]
    ir = ir / (np.sqrt(np.sum(ir ** 2, axis=0)) + 1e-12)
    w = np.stack([signal.fftconvolve(y[:, c], ir[:, c]) for c in range(2)], 1)
    w = w / (np.max(np.abs(w)) + 1e-12) * np.max(np.abs(y))
    out = np.zeros((len(w), 2))
    out[:len(y)] += y * (1 - wet)
    out += w * wet
    return out


def grains(src, dur, g, gmin=0.02, gmax=0.12, repeat=0.35, reverse=0.15, gap=0.1, xf=0.004):
    """Cut a recording into short grains and re-sequence them (stutters, dropouts, reversals)."""
    src = st(src)
    n = ns(dur)
    out = np.zeros((n, 2))
    i = 0
    k = ns(xf)
    while i < n:
        L = ns(g.u(gmin, gmax))
        a = int(g.u(0, max(1, len(src) - L)))
        gr = src[a:a + L].copy()
        if len(gr) < 2 * k + 2:
            break
        if g.u() < reverse:
            gr = gr[::-1]
        gr[:k] *= np.linspace(0, 1, k)[:, None]
        gr[-k:] *= np.linspace(1, 0, k)[:, None]
        reps = int(g.u(2, 5)) if g.u() < repeat else 1
        for _ in range(reps):
            if i >= n:
                break
            e = min(n, i + len(gr))
            out[i:e] += gr[:e - i]
            i += len(gr)
        if g.u() < gap:
            i += ns(g.u(0.01, 0.06))
    return out


def sweep_bp(y, f0, f1, width_oct=0.8, order=2, block=256):
    """Band-pass whose centre glides from f0 to f1 (log), for filtered sweeps of real noise."""
    y = st(y)
    n = len(y)
    fc = np.exp(np.linspace(np.log(f0), np.log(f1), n))
    out = np.zeros_like(y)
    zi = None
    for s in range(0, n, block):
        e = min(n, s + block)
        f = float(np.mean(fc[s:e]))
        lo, hi = f / 2 ** (width_oct / 2), min(f * 2 ** (width_oct / 2), SR / 2 * 0.95)
        sos = signal.butter(order, [max(lo, 20), hi], btype='bandpass', fs=SR, output='sos')
        if zi is None:
            zi = np.zeros((sos.shape[0], 2, 2))
        for c in range(2):
            out[s:e, c], zi[:, c] = signal.sosfilt(sos, y[s:e, c], zi=zi[:, c])
    return out


def chorus(y, depth=0.004, rate_hz=0.6, mix=0.5):
    """Two slowly drifting copies (hologram / projected-voice shimmer)."""
    y = st(y)
    n = len(y)
    t = np.arange(n) / SR
    out = y * (1 - mix)
    for c, ph in enumerate((0.0, np.pi / 2)):
        d = (depth * (1 + np.sin(2 * np.pi * rate_hz * t + ph)) / 2 + 0.002) * SR
        out[:, c] += np.interp(np.arange(n) - d, np.arange(n), y[:, c]) * mix
    return out


def tile(y, total, xf=1.0):
    """Repeat y with crossfades until it is `total` seconds long."""
    y = st(y)
    X = min(ns(xf), len(y) // 4)
    out = y.copy()
    while len(out) < ns(total):
        t = np.linspace(0, 1, X)[:, None]
        out = np.concatenate([out[:-X], out[-X:] * np.cos(t * np.pi / 2) + y[:X] * np.sin(t * np.pi / 2), y[X:]])
    return out[:ns(total)]


def seq(parts, length=0.0):
    end = max([int(round(t * SR)) + len(st(a)) for t, a in parts] + [ns(length)])
    out = np.zeros((end, 2))
    for t, a in parts:
        a = st(a)
        i = int(round(t * SR))
        out[i:i + len(a)] += a
    return out


def pan(y, p):
    a = (p + 1) * np.pi / 4
    return st(y) * np.array([np.cos(a), np.sin(a)]) * np.sqrt(2)


def env(y, pts):
    """Multiply by a piecewise-linear envelope [(t, gain), ...]."""
    y = st(y)
    t = np.arange(len(y)) / SR
    tt, gg = zip(*pts)
    return y * np.interp(t, tt, gg)[:, None]
