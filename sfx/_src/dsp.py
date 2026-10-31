"""Small DSP toolkit for the cyberpunk SFX pack.

Everything works on float64 numpy arrays at SR. Mono signals are 1-D,
stereo signals are shape (n, 2).
"""
import numpy as np
from scipy import signal

SR = 48000


class Gen:
    """Seeded random source so every sound is reproducible."""

    def __init__(self, seed):
        self.r = np.random.default_rng(seed)

    def white(self, dur):
        return self.r.standard_normal(ns(dur))

    def pink(self, dur):
        n = ns(dur)
        spec = np.fft.rfft(self.r.standard_normal(n))
        f = np.fft.rfftfreq(n, 1 / SR)
        f[0] = f[1]
        spec /= np.sqrt(f)
        x = np.fft.irfft(spec, n)
        return x / (np.std(x) + 1e-12)

    def brown(self, dur):
        x = np.cumsum(self.r.standard_normal(ns(dur)))
        x = hp(x, 15)
        return x / (np.std(x) + 1e-12)

    def u(self, a=0.0, b=1.0, size=None):
        return self.r.uniform(a, b, size)

    def jit(self, v, amt):
        """v scaled by a random factor in [1-amt, 1+amt]."""
        return v * self.r.uniform(1 - amt, 1 + amt)


def ns(dur):
    return int(round(dur * SR))


def tvec(n):
    return np.arange(n) / SR


def silence(dur, ch=1):
    return np.zeros(ns(dur)) if ch == 1 else np.zeros((ns(dur), 2))


# ---------------------------------------------------------------- filters
def _sos(kind, fc, order):
    if kind == 'bandpass':
        lo, hi = fc
        lo = max(lo, 5.0)
        hi = min(hi, SR / 2 * 0.98)
        return signal.butter(order, [lo, hi], btype='bandpass', fs=SR, output='sos')
    fc = min(max(fc, 5.0), SR / 2 * 0.98)
    return signal.butter(order, fc, btype=kind, fs=SR, output='sos')


def lp(x, fc, order=2):
    return signal.sosfilt(_sos('lowpass', fc, order), x, axis=0)


def hp(x, fc, order=2):
    return signal.sosfilt(_sos('highpass', fc, order), x, axis=0)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(_sos('bandpass', (lo, hi), order), x, axis=0)


def peak(x, fc, q, gain_db):
    """RBJ peaking EQ."""
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * fc / SR
    al = np.sin(w) / (2 * q)
    b = [1 + al * a, -2 * np.cos(w), 1 - al * a]
    aa = [1 + al / a, -2 * np.cos(w), 1 - al / a]
    return signal.lfilter(b, aa, x, axis=0)


def shelf_low(x, fc, gain_db):
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * fc / SR
    al = np.sin(w) / 2 * np.sqrt(2)
    c = np.cos(w)
    sa = 2 * np.sqrt(a) * al
    b = [a * ((a + 1) - (a - 1) * c + sa), 2 * a * ((a - 1) - (a + 1) * c), a * ((a + 1) - (a - 1) * c - sa)]
    aa = [(a + 1) + (a - 1) * c + sa, -2 * ((a - 1) + (a + 1) * c), (a + 1) + (a - 1) * c - sa]
    return signal.lfilter(b, aa, x, axis=0)


def svf(x, fc, q=0.707, mode='lp'):
    """Time-varying Chamberlin/TPT state-variable filter.

    fc may be a scalar or a per-sample array. Pure python loop, so keep
    the inputs short (a few seconds at most) or use block_filter.
    """
    n = len(x)
    fc = np.broadcast_to(np.asarray(fc, dtype=float), (n,))
    g = np.tan(np.pi * np.clip(fc, 10, SR * 0.45) / SR)
    k = 1.0 / q
    a1 = 1 / (1 + g * (g + k))
    a2 = g * a1
    a3 = g * a2
    ic1 = ic2 = 0.0
    out = np.empty(n)
    sel = {'lp': 0, 'bp': 1, 'hp': 2}[mode]
    for i in range(n):
        v0 = x[i]
        v3 = v0 - ic2
        v1 = a1[i] * ic1 + a2[i] * v3
        v2 = ic2 + a2[i] * ic1 + a3[i] * v3
        ic1 = 2 * v1 - ic1
        ic2 = 2 * v2 - ic2
        if sel == 0:
            out[i] = v2
        elif sel == 1:
            out[i] = v1
        else:
            out[i] = v0 - k * v1 - v2
    return out


def block_filter(x, fc_curve, kind='lowpass', order=2, block=256, width=None):
    """Time-varying Butterworth by blocks with carried state (fast)."""
    n = len(x)
    fc_curve = np.broadcast_to(np.asarray(fc_curve, dtype=float), (n,))
    out = np.empty(n)
    zi = None
    for s in range(0, n, block):
        e = min(n, s + block)
        f = float(np.mean(fc_curve[s:e]))
        if kind == 'bandpass':
            w = width if width is not None else f * 0.5
            sos = _sos('bandpass', (max(20, f - w / 2), f + w / 2), order)
        else:
            sos = _sos(kind, f, order)
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[s:e], zi = signal.sosfilt(sos, x[s:e], zi=zi)
    return out


# -------------------------------------------------------------- envelopes
def env_exp(n, tau, delay=0.0):
    t = tvec(n) - delay
    e = np.exp(-np.maximum(t, 0) / tau)
    e[t < 0] = 0
    return e


def env_ad(n, att, tau, delay=0.0, curve=1.0):
    """Linear(ish) attack then exponential decay."""
    t = tvec(n) - delay
    e = np.where(t < att, np.clip(t / max(att, 1e-6), 0, 1) ** curve, np.exp(-(t - att) / tau))
    e[t < 0] = 0
    return e


def env_points(n, pts):
    """Piecewise-linear envelope from [(time, value), ...]."""
    t = tvec(n)
    tt, vv = zip(*pts)
    return np.interp(t, tt, vv)


def fade(x, fin=0.002, fout=0.01):
    x = x.copy()
    a, b = ns(fin), ns(fout)
    if a > 0:
        r = np.linspace(0, 1, a)
        x[:a] = (x[:a].T * r).T
    if b > 0:
        r = np.linspace(1, 0, b) ** 2
        x[-b:] = (x[-b:].T * r).T
    return x


# --------------------------------------------------------------- sources
def sweep_sine(n, f0, f1, tau, phase=0.0, harmonics=None):
    """Sine whose frequency glides exponentially from f0 to f1 (time const tau)."""
    t = tvec(n)
    f = f1 + (f0 - f1) * np.exp(-t / tau)
    ph = 2 * np.pi * np.cumsum(f) / SR + phase
    y = np.sin(ph)
    if harmonics:
        for h, a in harmonics:
            y += a * np.sin(h * ph)
    return y


def osc(freq, n, shape='sine', phase=0.0):
    freq = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    ph = 2 * np.pi * np.cumsum(freq) / SR + phase
    if shape == 'sine':
        return np.sin(ph)
    if shape == 'saw':
        # PolyBLEP-free but oversampled-ish saw via additive up to nyquist/2
        y = np.zeros(n)
        fmax = float(np.max(freq))
        kmax = max(1, int((SR / 2.2) / max(fmax, 1)))
        for k in range(1, min(kmax, 60) + 1):
            y += ((-1) ** (k + 1)) * np.sin(k * ph) / k
        return y * (2 / np.pi)
    if shape == 'square':
        y = np.zeros(n)
        fmax = float(np.max(freq))
        kmax = max(1, int((SR / 2.2) / max(fmax, 1)))
        for k in range(1, min(kmax, 60) + 1, 2):
            y += np.sin(k * ph) / k
        return y * (4 / np.pi)
    if shape == 'tri':
        return 2 / np.pi * np.arcsin(np.sin(ph))
    raise ValueError(shape)


def modal(n, modes, delay=0.0, strike=None):
    """Bank of damped sinusoids: modes = [(freq, tau, amp), ...].

    strike: optional excitation (short array) convolved in for a softer hit.
    """
    t = tvec(n) - delay
    y = np.zeros(n)
    m = t >= 0
    tt = t[m]
    for f, tau, a in modes:
        if f >= SR / 2 * 0.95:
            continue
        y[m] += a * np.sin(2 * np.pi * f * tt) * np.exp(-tt / tau)
    if strike is not None:
        y = signal.fftconvolve(y, strike)[:n]
    k = min(n // 8, ns(0.05))
    if k > 1:
        y[-k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return y


def metal_modes(g, f0, count=14, tau=0.25, spread=1.0, bright=0.8):
    """Inharmonic plate/tube modes for metal hits."""
    ratios = np.array([1.0, 1.593, 2.136, 2.296, 2.653, 2.918, 3.156, 3.5, 3.6, 4.07,
                       4.23, 4.6, 5.13, 5.4, 5.93, 6.21, 6.8, 7.3])[:count]
    ratios = ratios * (1 + g.u(-0.02, 0.02, len(ratios)) * spread)
    out = []
    for i, r in enumerate(ratios):
        f = f0 * r
        out.append((f, tau * (0.9 ** i) * g.u(0.7, 1.2), (bright ** i) * g.u(0.5, 1.0)))
    return out


def crackle(g, n, density, tau=0.0004, lo=1500, hi=12000):
    """Random impulsive clicks (electric sparks, debris, vinyl...)."""
    y = np.zeros(n)
    dens = np.broadcast_to(np.asarray(density, dtype=float), (n,))
    p = dens / SR
    hits = np.nonzero(g.r.random(n) < p)[0]
    kl = ns(tau * 8) + 1
    dec = np.exp(-np.arange(kl) / (tau * SR))
    # a pool of different click shapes so repeated clicks don't share one spectrum
    pool = [dec * g.r.standard_normal(kl) for _ in range(48)]
    for h in hits:
        e = min(n, h + kl)
        k = pool[g.r.integers(len(pool))]
        y[h:e] += k[:e - h] * g.u(0.2, 1.0)
    return bp(y, lo, hi)


# ------------------------------------------------------------ nonlinear
def sat(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def bitcrush(x, bits=8, down=4):
    q = 2 ** (bits - 1)
    y = np.round(x * q) / q
    if down > 1:
        y = np.repeat(y[::down], down, axis=0)[:len(x)]
    return y


# ------------------------------------------------------------ space
def make_ir(g, rt60=1.2, predelay=0.01, early=None, lp_start=12000, lp_end=2500,
            width=1.0, dur=None, low_rt_mult=1.3, tail_energy=0.6, low_amt=1.0):
    """Stereo synthetic impulse response, scaled relative to a unit direct sound.

    early: list of (time_s, amplitude, lowpass_hz) discrete reflections
           (amplitude 1.0 == as loud as the direct sound).
    tail_energy: energy of the diffuse tail relative to the direct impulse.
    The tail is decaying noise whose brightness falls over time (air
    absorption) and whose lows ring a little longer.
    """
    dur = dur or (rt60 * 1.15 * max(1.0, low_rt_mult) + predelay + 0.05)
    n = ns(dur)
    ir = np.zeros((n, 2))
    t = tvec(n)
    tau = rt60 / 6.91
    win = np.ones(n)
    k = ns(min(0.4, dur * 0.25))
    win[-k:] = np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    for ch in range(2):
        nz = g.r.standard_normal(n)
        d = predelay + (0.0007 * ch * width)
        onset = np.clip((t - d) / 0.04, 0, 1) ** 1.5
        env = np.exp(-np.maximum(t - d, 0) / tau) * onset
        lows = lp(nz, 350) * np.exp(-np.maximum(t - d, 0) / (tau * low_rt_mult)) * onset
        fc = lp_end + (lp_start - lp_end) * np.exp(-np.maximum(t - d, 0) / (rt60 / 3))
        body = block_filter(nz * env, fc, 'lowpass', order=1, block=512)
        tail = (hp(body, 350) + lows * 2.2 * low_amt) * win
        ir[:, ch] = tail
    # Calibrate against pink noise (a fair stand-in for real program material):
    # output energy / input energy == tail_energy.
    ref = Gen(7).pink(0.5)
    num = sum(np.sum(signal.fftconvolve(ref, ir[:, ch]) ** 2) for ch in range(2)) / 2
    ir *= np.sqrt(tail_energy / (num / np.sum(ref ** 2) + 1e-12))
    if early:
        for tm, gain, lpf in early:
            imp = np.zeros(ns(0.006))
            imp[0] = 1
            kern = lp(imp, lpf, 2)
            side = 1 if g.u() > 0.5 else 0
            for ch in range(2):
                i = ns(tm) + (ns(g.u(0.0002, 0.0012) * width) if ch != side else 0)
                if i < n:
                    e = min(n, i + len(kern))
                    pan = 1.0 if ch == side else g.u(0.35, 0.8)
                    ir[i:e, ch] += kern[:e - i] * gain * pan
    return ir


def convolve(x, ir):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    n = len(x) + len(ir) - 1
    out = np.zeros((n, 2))
    for ch in range(2):
        out[:, ch] = signal.fftconvolve(x[:, ch], ir[:, ch])
    return out


def stereo(x, pan=0.0):
    """Constant-power pan. pan in [-1, 1]."""
    if x.ndim == 2:
        return x
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1) * np.sqrt(2)


def autopan(x, pan_curve):
    n = len(x)
    p = np.broadcast_to(np.asarray(pan_curve, dtype=float), (n,))
    a = (p + 1) * np.pi / 4
    if x.ndim == 1:
        return np.stack([x * np.cos(a), x * np.sin(a)], 1) * np.sqrt(2)
    return np.stack([x[:, 0] * np.cos(a), x[:, 1] * np.sin(a)], 1) * np.sqrt(2)


def mix(*parts, length=None):
    """Sum arrays (mono or stereo) placed at offsets: parts are (offset_s, arr, gain)."""
    end = 0
    for off, a, _ in parts:
        end = max(end, ns(off) + len(a))
    if length:
        end = max(end, ns(length))
    out = np.zeros((end, 2))
    for off, a, gain in parts:
        s = ns(off)
        a2 = stereo(a) if a.ndim == 1 else a
        out[s:s + len(a2)] += a2 * gain
    return out


def place(dst, src, offset, gain=1.0):
    s = ns(offset)
    if s >= len(dst):
        return dst
    src = stereo(src) if (dst.ndim == 2 and src.ndim == 1) else src
    e = min(len(dst), s + len(src))
    dst[s:e] += src[:e - s] * gain
    return dst


def doppler(x, dist_curve, c=343.0):
    """Variable delay read (distance in metres per sample) -> pitch shift + 1/r gain."""
    n = len(x)
    d = np.broadcast_to(np.asarray(dist_curve, dtype=float), (n,))
    delay = d / c * SR
    idx = np.arange(n) - delay
    y = np.interp(idx, np.arange(n), x, left=0, right=0)
    return y / np.maximum(d, 1.0)


# ------------------------------------------------------------ dynamics / mastering
def compress(x, thresh_db=-18, ratio=4, att=0.002, rel=0.08, makeup_db=0.0):
    mono = np.max(np.abs(x), axis=1) if x.ndim == 2 else np.abs(x)
    a_a = np.exp(-1 / (att * SR))
    a_r = np.exp(-1 / (rel * SR))
    lvl = signal.lfilter([1 - a_r], [1, -a_r], mono)  # cheap smooth; refine with attack
    lvl = np.maximum(lvl, signal.lfilter([1 - a_a], [1, -a_a], mono))
    db = 20 * np.log10(lvl + 1e-9)
    over = np.maximum(db - thresh_db, 0)
    gr = -over * (1 - 1 / ratio) + makeup_db
    gain = 10 ** (gr / 20)
    return (x.T * gain).T if x.ndim == 2 else x * gain


def limiter(x, ceiling_db=-1.0, lookahead=0.003, rel=0.06):
    ceil = 10 ** (ceiling_db / 20)
    st = x if x.ndim == 2 else x[:, None]
    pk = np.max(np.abs(st), axis=1)
    la = ns(lookahead)
    # gain needed per sample
    need = np.minimum(1.0, ceil / (pk + 1e-12))
    # look-ahead: min over upcoming window
    from scipy.ndimage import minimum_filter1d
    need = minimum_filter1d(need, size=2 * la + 1, origin=0)
    # smooth release (attack is instantaneous thanks to lookahead window)
    g = np.empty_like(need)
    a_r = np.exp(-1 / (rel * SR))
    cur = 1.0
    for i in range(len(need)):
        v = need[i]
        cur = v if v < cur else v + (cur - v) * a_r
        g[i] = cur
    # attack smoothing to avoid clicks
    g = signal.lfilter([1 - np.exp(-1 / (0.0007 * SR))], [1, -np.exp(-1 / (0.0007 * SR))], g)
    g = np.minimum(g, need * 1.0 + (1 - need) * 0)  # never exceed the needed gain
    y = (st.T * g).T
    y = np.clip(y, -ceil, ceil)
    return y if x.ndim == 2 else y[:, 0]


def seamless(y, loop_len, xfade):
    """y must be at least loop_len + xfade long. Returns loop_len samples that loop seamlessly."""
    L, X = ns(loop_len), ns(xfade)
    out = y[:L].copy()
    t = np.linspace(0, 1, X)
    fi = np.sin(t * np.pi / 2)
    fo = np.cos(t * np.pi / 2)
    if y.ndim == 2:
        fi, fo = fi[:, None], fo[:, None]
    out[:X] = y[:X] * fi + y[L:L + X] * fo
    return out
