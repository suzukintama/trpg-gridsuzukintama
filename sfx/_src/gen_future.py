"""Near-future electronics (2026-11-03): the hacking set rebuilt, terminal and phone notices, role gadgets.

The v7 hacking set was cut from real machines (56k modems, CRTs, hard drives), which the GM found dated.
These are synthesised instead, aiming at the 2077 / Deus Ex side of things rather than 8-bit game chirps:
glassy sine tones with a short inharmonic partial, sub-bass swells, band-passed noise sweeps, granular
"data" sparkle and clean digital stutters, all placed in a small bright room with a ping-pong echo.
  05_ハッキング/*      the electronic hacking sounds (same file names as before, so table setups keep working)
  10_端末・通知/*      holophone, messages, payments, AR windows, optics zoom, body scan, news flash
  11_職業別/<role>_*   the synthesised role gadgets (smartlink lock, optical camo, sandevistan, defibrillator, ...)
  07_環境音ループ/メドテック_生体モニター  a patient monitor loop
  python gen_future.py [hack|ui|role|loop]
"""
import sys

import numpy as np

from dsp import SR, Gen, ns, lp, hp, bp, env_ad, env_points, block_filter, make_ir, convolve, stereo, autopan, place, bitcrush, sat
from master import export

D5, D10, D11, D7 = '05_ハッキング/', '10_端末・通知/', '11_職業別/', '07_環境音ループ/'


def tv(n):
    return np.arange(n) / SR


def tail(x, fout=0.02):
    x = x.copy()
    k = min(ns(fout), len(x))
    x[-k:] *= np.linspace(1, 0, k) ** 2
    return x


def tone(f, dur, att=0.004, tau=0.15, fm=0.0, ratio=2.0, glide=None, partial=0.22, shape=None):
    """Glassy UI tone: sine + a fast inharmonic partial + a whisper of FM. glide=(tau, f_end)."""
    n = ns(dur)
    t = tv(n)
    fr = glide[1] + (f - glide[1]) * np.exp(-t / glide[0]) if glide else np.full(n, float(f))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    y = np.sin(ph + fm * np.sin(ph * ratio) * np.exp(-t / max(tau * 0.6, 1e-3)))
    y += partial * np.sin(ph * 2.76) * np.exp(-t / (tau * 0.25)) + 0.12 * np.sin(ph * 2) * np.exp(-t / tau)
    env = env_ad(n, att, tau) if shape is None else shape(n)
    return tail(y * env)


def pad(f, dur, att=0.05, rel=0.2, detune=0.004, voices=3):
    """Soft detuned sine/triangle pad, for sustained notes."""
    n = ns(dur)
    y = np.zeros(n)
    for k in range(voices):
        d = 1 + detune * (k - (voices - 1) / 2)
        ph = 2 * np.pi * f * d * tv(n)
        y += np.sin(ph) + 0.25 * (2 / np.pi) * np.arcsin(np.sin(ph * 2))
    return y / voices * env_points(n, [(0, 0), (att, 1), (max(att, dur - rel), 1), (dur, 0)])


def sub(dur, f0=90, f1=32, tau=0.18, att=0.003):
    n = ns(dur)
    t = tv(n)
    fr = f1 + (f0 - f1) * np.exp(-t / tau)
    return tail(np.sin(2 * np.pi * np.cumsum(fr) / SR) * env_ad(n, att, dur / 3))


def sweep(g, dur, f0, f1, peak=0.5, width=0.6, curve=1.0):
    """Band-passed noise whose centre moves f0 -> f1, swelling to `peak` (fraction of dur)."""
    n = ns(dur)
    x = g.r.standard_normal(n)
    fc = f0 * (f1 / f0) ** (np.linspace(0, 1, n) ** curve)
    y = block_filter(x, fc, 'bandpass', order=2, block=128, width=None) if width is None else \
        _bp_var(x, fc, width)
    e = env_points(n, [(0, 0), (dur * peak, 1), (dur, 0)]) ** 1.5
    return y * e / (np.std(y) + 1e-9) * 0.3


def _bp_var(x, fc, width):
    out = np.empty(len(x))
    from scipy import signal
    zi = None
    for s in range(0, len(x), 128):
        e = min(len(x), s + 128)
        f = float(np.mean(fc[s:e]))
        lo, hi = max(30, f * (1 - width / 2)), min(SR * 0.45, f * (1 + width / 2))
        sos = signal.butter(2, (lo, hi), 'bandpass', fs=SR, output='sos')
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[s:e], zi = signal.sosfilt(sos, x[s:e], zi=zi)
    return out


def grains(g, dur, rate, lo=1800, hi=7000, glen=(0.008, 0.03), amp=0.2, pan=0.8):
    """Granular 'data' sparkle: many tiny sine blips at random pitches, panned around."""
    out = np.zeros((ns(dur) + ns(0.05), 2))
    t = 0.0
    while t < dur:
        m = ns(g.u(*glen))
        f = np.exp(g.u(np.log(lo), np.log(hi)))
        bl = np.sin(2 * np.pi * f * tv(m)) * np.hanning(m) * g.u(0.3, 1.0)
        place(out, stereo(bl, g.u(-pan, pan)), t, amp)
        t += g.r.exponential(1 / rate)
    return out


def click(g, amp=0.5, hpf=2500):
    m = ns(0.006)
    x = hp(g.r.standard_normal(m), hpf) * np.exp(-tv(m) / 0.0009)
    return x * amp


def stutter(x, seg, reps, decay=0.85):
    """Repeat the first `seg` seconds `reps` times, each a little quieter: a digital buffer stutter."""
    m = ns(seg)
    piece = x[:m].copy()
    k = min(ns(0.002), m // 4)
    piece[:k] *= np.linspace(0, 1, k)[:, None] if piece.ndim == 2 else np.linspace(0, 1, k)
    piece[-k:] *= np.linspace(1, 0, k)[:, None] if piece.ndim == 2 else np.linspace(1, 0, k)
    return np.concatenate([piece * decay ** i for i in range(reps)])


def pingpong(x, dt=0.13, fb=0.38, taps=5, lpf=6000):
    x = stereo(x) if x.ndim == 1 else x
    out = np.zeros((len(x) + ns(dt * (taps + 1)), 2))
    out[:len(x)] += x
    y = x
    for i in range(1, taps + 1):
        y = lp(y, lpf) * fb
        ch = i % 2
        z = np.zeros_like(y)
        z[:, ch] = y.mean(1) * 1.4
        place(out, z, dt * i)
    return out


_IR = {}


def space(x, rt=0.5, wet=0.22, seed=1):
    key = (rt, seed)
    if key not in _IR:
        _IR[key] = make_ir(Gen(seed), rt60=rt, predelay=0.012, lp_start=14000, lp_end=5000, tail_energy=0.5)
    x = stereo(x) if x.ndim == 1 else x
    w = convolve(x, _IR[key])
    out = w * wet
    out[:len(x)] += x
    return out


def seq(parts, length=None):
    """parts: (t, x, gain[, pan]) -> stereo buffer."""
    end = max(ns(p[0]) + len(p[1]) for p in parts)
    out = np.zeros((max(end, ns(length or 0)), 2))
    for p in parts:
        t, x, gn = p[:3]
        pn = p[3] if len(p) > 3 else 0.0
        place(out, stereo(x, pn) if x.ndim == 1 else x, t, gn)
    return out


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ================================================================ 05 hacking
def hack():
    g = Gen(5100)

    # deck power-up: a rising whine and a soft swell into a three-note boot chord
    n = ns(1.4)
    whine = np.sin(2 * np.pi * np.cumsum(200 + 2600 * (np.linspace(0, 1, n) ** 2.2)) / SR) * env_points(n, [(0, 0), (1.1, 0.5), (1.4, 0)])
    chord = sum(tone(hz(m), 2.2, att=0.02, tau=0.8, partial=0.1) for m in (69, 76, 81)) / 3
    x = seq([(0, click(g, 0.6), 1), (0.02, lp(whine, 6000) * 0.12, 1), (0.05, sweep(g, 1.3, 300, 6000, 0.9, 0.5), 0.8),
             (1.25, chord, 0.6), (1.25, sub(0.8, 70, 45), 0.35), (1.3, grains(g, 0.6, 60, 3000, 9000, amp=0.12), 1)])
    export(D5 + 'デッキ起動', space(pingpong(x, 0.11, 0.25, 3), 0.6), -17)

    # deck power-down: whine falls, a last low blip, a relay-like click
    n = ns(1.3)
    fall = np.sin(2 * np.pi * np.cumsum(3000 * np.exp(-tv(n) / 0.35) + 60) / SR) * env_points(n, [(0, 0.5), (1.3, 0)])
    x = seq([(0, tone(hz(76), 0.5, tau=0.12), 0.5), (0.08, tone(hz(64), 0.6, tau=0.15), 0.45),
             (0.15, lp(fall, 5000) * 0.14, 1), (0.15, sweep(g, 1.1, 5000, 200, 0.1, 0.5), 0.6), (1.35, click(g, 0.7, 1500), 1)])
    export(D5 + 'デッキ電源断', space(x, 0.5), -18)

    # jack in: connector click, a sub swell and riser that bloom into a shimmering hum
    n = ns(2.2)
    rise = sweep(g, 2.2, 150, 9000, 0.95, 0.4, curve=1.6)
    riser = np.sin(2 * np.pi * np.cumsum(80 * (40 ** (np.linspace(0, 1, n) ** 2))) / SR) * env_points(n, [(0, 0), (2.1, 0.35), (2.2, 0)])
    bloom = sum(pad(hz(m), 2.6, att=0.01, rel=1.8, detune=0.006) for m in (45, 57, 64, 69)) / 4
    x = seq([(0, click(g, 0.9, 1200), 1), (0.01, click(g, 0.5, 4000), 1), (0.15, sub(2.0, 30, 60, 1.0, att=1.6), 0.5),
             (0.15, rise, 1), (0.15, lp(riser, 7000), 0.12), (2.35, bloom, 0.45), (2.35, sub(1.5, 110, 38, 0.12), 0.7),
             (2.35, sweep(g, 1.6, 8000, 400, 0.02, 0.8), 0.9), (2.4, grains(g, 1.8, 90, 2500, 10000, amp=0.1), 1)])
    export(D5 + 'ジャックイン', space(x, 0.9, 0.25), -15)

    # jack out: the hum folds downward and cuts with a click
    n = ns(1.2)
    fold = sum(pad(hz(m), 1.2, att=0.005, rel=0.9) for m in (57, 64, 69)) / 3
    fold = np.interp(np.cumsum(np.linspace(1.0, 0.25, n)), np.arange(n), fold)
    x = seq([(0, fold, 0.5), (0, sweep(g, 1.1, 7000, 150, 0.05, 0.5), 0.9), (0, sub(1.0, 70, 30, 0.3, 0.01), 0.4),
             (1.15, click(g, 0.9, 1200), 1)])
    export(D5 + 'ジャックアウト', space(x, 0.6), -16)

    # net handshake: a quick rising run of tones that lock into one, replacing the 56k modem
    parts = []
    for i, m in enumerate([72, 79, 76, 84, 81, 88, 86, 91]):
        parts.append((i * 0.055, tone(hz(m), 0.2, tau=0.04, partial=0.3), 0.4, (-0.6 if i % 2 else 0.6)))
    parts += [(0.5, tone(hz(84), 0.9, tau=0.3, fm=0.6), 0.55), (0.5, tone(hz(91), 0.9, tau=0.25), 0.3),
              (0.0, grains(g, 0.5, 120, 4000, 11000, amp=0.12), 1), (0.45, sweep(g, 0.5, 2000, 9000, 0.9, 0.5), 0.6)]
    export(D5 + 'ネット接続', space(pingpong(seq(parts), 0.09, 0.3, 4)), -18)

    # access granted: three rising glass notes and an airy lift
    x = seq([(0, tone(hz(76), 0.6, tau=0.18), 0.5, -0.3), (0.09, tone(hz(83), 0.6, tau=0.18), 0.5, 0.3),
             (0.18, tone(hz(88), 1.2, tau=0.45, fm=0.4), 0.6), (0.05, sweep(g, 0.6, 1500, 8000, 0.8, 0.5), 0.5)])
    export(D5 + 'アクセス許可', space(pingpong(x, 0.12, 0.25, 3)), -18)

    # access denied: two low falling tones with a filtered buzz, then a dull lock
    def deny(f):
        n = ns(0.32)
        buzz = lp(np.sign(np.sin(2 * np.pi * f * tv(n))) * 0.3, 1800) * env_ad(n, 0.004, 0.1)
        return tone(f * 2, 0.32, tau=0.12, glide=(0.2, f * 1.9), partial=0.1) * 0.6 + buzz
    x = seq([(0, deny(hz(52)), 0.7), (0.2, deny(hz(49)), 0.7), (0.42, sub(0.3, 120, 50, 0.05), 0.5), (0.42, click(g, 0.4, 800), 1)])
    export(D5 + 'アクセス拒否', space(x, 0.4), -17)

    # electronic lock release: a soft chirp, then the mag-lock letting go
    x = seq([(0, tone(hz(84), 0.25, tau=0.05), 0.4), (0.07, tone(hz(91), 0.4, tau=0.12), 0.45),
             (0.22, sub(0.25, 160, 60, 0.03), 0.5), (0.22, click(g, 0.7, 900), 1), (0.24, sweep(g, 0.35, 3000, 500, 0.05, 0.6), 0.5)])
    export(D5 + '電子ロック解除', space(x, 0.45), -18)

    # scan: a band of noise and a chirp sweep left to right, ending in a ping
    n = ns(1.8)
    band = sweep(g, 1.8, 600, 6000, 0.5, 0.25)
    chirps = np.zeros(n)
    for k in range(10):
        m = ns(0.05)
        chirps[ns(k * 0.17):ns(k * 0.17) + m] += np.sin(2 * np.pi * (2400 + 300 * k) * tv(m)) * np.hanning(m)
    body = autopan(band + chirps * 0.12, np.linspace(-0.9, 0.9, n))
    x = seq([(0, body, 1), (1.85, tone(hz(93), 1.0, tau=0.3, fm=0.5), 0.45), (1.85, tone(hz(81), 1.0, tau=0.3), 0.3)])
    export(D5 + 'スキャン', space(pingpong(x, 0.1, 0.25, 3)), -18)

    # data transfer: steady pulse under a stream of granular sparkle (4 s)
    L = 4.0
    pulse = np.zeros(ns(L))
    for k in range(int(L / 0.125)):
        pulse = place(pulse, tone(hz(88 if k % 4 == 0 else 81), 0.08, tau=0.02, partial=0.0), k * 0.125, 0.25 if k % 4 == 0 else 0.12)
    n = ns(L)
    hum = (np.sin(2 * np.pi * 110 * tv(n)) * 0.5 + np.sin(2 * np.pi * 220.7 * tv(n)) * 0.3) * env_points(n, [(0, 0), (0.3, 1), (L - 0.4, 1), (L, 0)])
    x = seq([(0, stereo(pulse), 1), (0, grains(g, L - 0.3, 160, 2500, 10000, amp=0.13), 1), (0, hum, 0.08),
             (0, sweep(g, L, 3000, 5000, 0.5, 0.3), 0.25)])
    export(D5 + 'データ転送', space(x, 0.5, 0.15), -19)

    # quickhack: a 0.45 s charge, then a zap that streaks across, with sparkle trailing behind
    n = ns(0.5)
    charge = np.sin(2 * np.pi * np.cumsum(300 * (12 ** np.linspace(0, 1, n))) / SR) * np.linspace(0, 1, n) ** 2
    m = ns(0.6)
    zap = np.sin(2 * np.pi * np.cumsum(5200 * np.exp(-tv(m) / 0.08) + 180) / SR) * env_ad(m, 0.002, 0.12)
    zap = sat(zap * 1.5 + 0.3 * bitcrush(zap, 6, 3), 1.2)
    x = seq([(0, lp(charge, 8000), 0.25), (0, sweep(g, 0.5, 800, 9000, 1.0, 0.4, curve=2), 0.7),
             (0.5, autopan(zap, np.linspace(-0.7, 0.8, m)), 0.5), (0.5, sub(0.4, 140, 45, 0.05), 0.6),
             (0.5, sweep(g, 0.6, 9000, 1500, 0.03, 0.5), 0.8), (0.55, grains(g, 0.7, 140, 3000, 11000, amp=0.12), 1)])
    export(D5 + 'クイックハック送信', space(pingpong(x, 0.1, 0.3, 4), 0.5), -15)

    # ICE breach: shattering digital glass, a bass drop and falling shards
    n = ns(1.2)
    shards = np.zeros(n)
    for k in range(26):
        f = g.u(1500, 9000)
        t0 = g.r.exponential(0.12)
        m = ns(g.u(0.05, 0.4))
        s = np.sin(2 * np.pi * f * np.exp(-tv(m) / 0.5) * tv(m)) * np.exp(-tv(m) / g.u(0.03, 0.15))
        shards = place(shards, s, t0, g.u(0.05, 0.2))
    burst = hp(g.r.standard_normal(ns(0.3)), 1500) * env_ad(ns(0.3), 0.001, 0.05)
    x = seq([(0, burst, 0.5), (0, stereo(shards), 0.8), (0, sub(1.0, 100, 28, 0.2), 0.8),
             (0, sweep(g, 1.2, 9000, 300, 0.02, 0.6), 0.7), (0.05, tone(hz(60), 1.2, tau=0.4, glide=(0.5, hz(48)), fm=1.5), 0.3)])
    export(D5 + 'ICE突破', space(x, 0.8, 0.3), -14)

    # ICE alert: a sub thud, then a detuned rising two-tone pulse three times, glitched at the end
    def whoop(dur=0.55):
        m = ns(dur)
        f = hz(62) * (1.6 ** np.linspace(0, 1, m))
        y = sum(np.sin(2 * np.pi * np.cumsum(f * (1 + d)) / SR) for d in (-0.006, 0, 0.007)) / 3
        y += 0.35 * lp(np.sign(np.sin(2 * np.pi * np.cumsum(f / 2) / SR)), 1400)
        return y * env_points(m, [(0, 0), (0.03, 1), (dur - 0.06, 1), (dur, 0)])
    w = whoop()
    x = seq([(0, sub(0.6, 80, 35, 0.1), 0.8), (0, click(g, 0.6, 600), 1)] +
            [(0.12 + i * 0.62, w, 0.35, (-0.3, 0.3, 0)[i]) for i in range(3)])
    gl = stutter(x[ns(1.45):ns(1.53)], 0.04, 5, 0.8)
    x = place(x, gl * 0.6, 1.9)
    export(D5 + 'ICE検知_警告', space(x, 0.6, 0.2), -14)

    # trace: pings that speed up and climb as the trace closes in
    parts, t, k = [], 0.0, 0
    while t < 3.6:
        parts.append((t, tone(hz(79 + min(k, 14)), 0.25, tau=0.05, partial=0.35), 0.4, (-0.5 if k % 2 else 0.5)))
        t += 0.42 * 0.85 ** k + 0.07
        k += 1
    parts.append((t + 0.05, tone(hz(96), 1.2, tau=0.5, fm=0.8), 0.45))
    parts.append((t + 0.05, sub(0.5, 90, 40, 0.1), 0.5))
    export(D5 + '逆探知される', space(pingpong(seq(parts), 0.08, 0.2, 2)), -17)

    # password crack: a fast tick of digits locking one by one, then the success chime
    parts, t = [], 0.0
    for d in range(6):
        for k in range(7):
            parts.append((t, tone(g.u(2000, 4200), 0.03, tau=0.006, partial=0.0), 0.18, g.u(-0.4, 0.4)))
            t += 0.03
        parts.append((t, tone(hz(84 + d * 2), 0.18, tau=0.05), 0.35))
        t += 0.06
    parts += [(t + 0.05, tone(hz(84), 1.0, tau=0.35), 0.4), (t + 0.05, tone(hz(91), 1.0, tau=0.35), 0.35),
              (t + 0.05, tone(hz(96), 1.2, tau=0.45, fm=0.4), 0.3)]
    export(D5 + 'パスワード解読', space(seq(parts)), -18)

    # virus / daemon upload: a dark wobbling FM drone that crawls down, bit-crushed in places
    n = ns(2.4)
    t = tv(n)
    f = hz(45) * (1 - 0.25 * t / 2.4)
    ph = 2 * np.pi * np.cumsum(f) / SR
    wob = np.sin(ph + 3.0 * np.sin(ph * 1.5) * (0.5 + 0.5 * np.sin(2 * np.pi * 5 * t)))
    wob = wob * env_points(n, [(0, 0), (0.15, 1), (2.0, 0.8), (2.4, 0)])
    crushed = bitcrush(wob, 5, 6) * (np.sin(2 * np.pi * 1.7 * t) > 0.6)
    x = seq([(0, lp(wob, 3000), 0.4), (0, lp(crushed, 6000), 0.15), (0, grains(g, 2.2, 50, 800, 3000, amp=0.15), 1),
             (0, sub(2.2, 55, 40, 1.0, 0.1), 0.35)])
    export(D5 + 'ウイルス注入', space(x, 0.7, 0.25), -17)

    # system glitch: a clean tone run that stutters, drops out and crunches (2.2 s)
    base = seq([(i * 0.12, tone(hz(m), 0.3, tau=0.1, fm=0.8), 0.5) for i, m in enumerate([81, 76, 88, 84, 79, 91, 86, 83])] +
               [(0, sweep(g, 1.2, 2000, 6000, 0.5, 0.4), 0.6)])
    out = np.zeros((ns(2.4), 2))
    t, src = 0.0, 0.0
    while t < 2.1:
        r = g.u()
        if r < 0.35:
            piece = stutter(base[ns(src):ns(src + 0.06)], g.u(0.015, 0.05), int(g.u(3, 8)))
        elif r < 0.55:
            piece = bitcrush(base[ns(src):ns(src + 0.12)], 4, int(g.u(4, 12))) * 0.7
        elif r < 0.7:
            piece = np.zeros((ns(g.u(0.03, 0.09)), 2))
        else:
            piece = base[ns(src):ns(src + g.u(0.05, 0.15))]
        place(out, piece, t)
        t += len(piece) / SR
        src = (src + g.u(0.03, 0.2)) % 0.9
    export(D5 + 'システム異常_グリッチ', space(out, 0.4, 0.15), -17)

    # facility lockdown: a low two-tone alarm pulse with a heavy door slam in the middle (6 s)
    def two_tone(m1, m2, dur=0.5):
        m = ns(dur)
        f = np.where(tv(m) < dur / 2, hz(m1), hz(m2))
        y = sum(np.sin(2 * np.pi * np.cumsum(f * d) / SR) for d in (1, 1.005, 2.003)) / 3
        y = sat(y * 1.4 + 0.3 * lp(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)), 2000), 1.3)
        return y * env_points(m, [(0, 0), (0.01, 1), (dur - 0.03, 1), (dur, 0)])
    parts = [(i * 0.75, two_tone(67, 62), 0.3) for i in range(8)]
    slam = seq([(0, sub(0.8, 70, 30, 0.08), 1), (0, lp(g.r.standard_normal(ns(0.5)), 900) * env_ad(ns(0.5), 0.002, 0.08), 0.9),
                (0.0, sweep(g, 0.9, 400, 2500, 0.1, 0.8), 0.6)])
    parts += [(2.3, slam, 0.9), (2.25, sweep(g, 0.25, 1000, 300, 0.5, 0.6), 0.6)]
    export(D5 + '警報_施設ロックダウン', space(seq(parts), 1.4, 0.3), -15)

    # flatline (net): heartbeat-like pulses slowing, then one sustained chorused tone over static
    def beat(f=hz(81)):
        return tone(f, 0.35, tau=0.09, partial=0.15) + 0.25 * sub(0.35, 90, 50, 0.05)
    parts = [(0, beat(), 0.5), (0.8, beat(), 0.47), (1.5, beat(), 0.43), (2.1, beat(), 0.4)]
    n = ns(3.0)
    long_ = pad(hz(81), 3.0, att=0.01, rel=0.8, detune=0.003)
    static = hp(g.r.standard_normal(n), 3000) * env_points(n, [(0, 0), (0.8, 1), (3.0, 0)]) * 0.04
    parts += [(2.7, long_, 0.4), (2.7, static, 1), (2.7, grains(g, 2.5, 40, 300, 1500, amp=0.06), 1)]
    export(D5 + 'フラットライン', space(seq(parts), 0.8, 0.25), -18)


# ================================================================ 10 terminal / phone / AR
def ui():
    g = Gen(5200)

    # holophone ring: a rising four-note figure with a bell partial, twice, with a pause (5 s)
    def ring():
        return seq([(i * 0.11, tone(hz(m), 0.7, tau=0.25, fm=0.5, ratio=3.5), 0.4, (-0.3, 0.3, -0.15, 0.15)[i])
                    for i, m in enumerate([79, 83, 86, 91])] + [(0.33, tone(hz(95), 1.0, tau=0.4), 0.2)])
    r = ring()
    export(D10 + 'ホロフォン_着信', space(pingpong(seq([(0, r, 1), (0.6, r, 0.9), (2.4, r, 1), (3.0, r, 0.9)]), 0.14, 0.2, 2)), -18)

    x = seq([(0, tone(hz(76), 0.4, tau=0.1), 0.45), (0.07, tone(hz(83), 0.6, tau=0.2), 0.45),
             (0.0, sweep(g, 0.45, 1000, 7000, 0.85, 0.5), 0.4), (0.12, grains(g, 0.4, 80, 4000, 10000, amp=0.1), 1)])
    export(D10 + 'ホロコール_接続', space(x), -19)
    x = seq([(0, tone(hz(83), 0.4, tau=0.1), 0.45), (0.08, tone(hz(76), 0.6, tau=0.18), 0.45),
             (0.0, sweep(g, 0.4, 6000, 800, 0.1, 0.5), 0.4)])
    export(D10 + 'ホロコール_切断', space(x), -19)

    x = seq([(0, tone(hz(88), 0.5, tau=0.12, fm=0.4), 0.45), (0.1, tone(hz(93), 0.7, tau=0.22), 0.4)])
    export(D10 + 'メッセージ受信', space(pingpong(x, 0.1, 0.25, 2)), -19)

    # payment done: a coin-bright chord bloom and a soft lift
    x = seq([(0, tone(hz(84), 1.0, tau=0.3), 0.35), (0.05, tone(hz(88), 1.0, tau=0.3), 0.3),
             (0.1, tone(hz(91), 1.3, tau=0.4, fm=0.5), 0.35), (0.1, tone(hz(96), 1.3, tau=0.5), 0.2),
             (0.0, sweep(g, 0.5, 2000, 9000, 0.8, 0.4), 0.35), (0.12, grains(g, 0.6, 90, 5000, 12000, amp=0.09), 1)])
    export(D10 + '送金完了', space(pingpong(x, 0.11, 0.25, 3)), -18)
    x = seq([(0, tone(hz(64), 0.3, tau=0.08, partial=0.05), 0.5), (0.16, tone(hz(64), 0.3, tau=0.08, partial=0.05), 0.5),
             (0.32, tone(hz(59), 0.6, tau=0.2, partial=0.05), 0.5)])
    export(D10 + '残高不足', space(x, 0.4), -18)

    # AR window open / close: an airy swish with a pop on top
    x = seq([(0, sweep(g, 0.3, 1500, 9000, 0.85, 0.5), 0.7), (0.24, tone(hz(91), 0.3, tau=0.06, partial=0.4), 0.35)])
    export(D10 + 'AR_ウィンドウ表示', space(x, 0.35), -20)
    x = seq([(0, tone(hz(86), 0.2, tau=0.04, partial=0.4), 0.35), (0.04, sweep(g, 0.28, 8000, 1200, 0.1, 0.5), 0.7)])
    export(D10 + 'AR_ウィンドウ閉じる', space(x, 0.35), -20)
    x = seq([(0, tone(hz(93), 0.35, tau=0.08, fm=1.0, ratio=1.5), 0.4), (0.0, click(g, 0.3, 5000), 1)])
    export(D10 + 'AR_マーカー', space(pingpong(x, 0.07, 0.3, 3), 0.3), -20)

    # optics zoom: tiny servo whir climbing in steps, each step a focus tick
    parts = []
    for k in range(4):
        m = ns(0.16)
        whir = np.sin(2 * np.pi * np.cumsum(np.linspace(1800 + 300 * k, 2600 + 300 * k, m)) / SR) * np.hanning(m)
        parts += [(k * 0.22, whir, 0.12), (k * 0.22, sweep(g, 0.16, 3000, 6000, 0.5, 0.3), 0.3), (k * 0.22 + 0.16, click(g, 0.35, 4000), 1)]
    parts.append((0.9, tone(hz(96), 0.3, tau=0.06), 0.25))
    export(D10 + '視覚_ズーム', space(seq(parts), 0.3, 0.15), -20)

    # body scan: a slow beam top to bottom, a soft tick per section, a result tone
    n = ns(2.4)
    beam = sweep(g, 2.4, 6000, 900, 0.5, 0.3) + 0.15 * np.sin(2 * np.pi * 1200 * tv(n)) * env_points(n, [(0, 0), (0.3, 1), (2.2, 1), (2.4, 0)])
    parts = [(0, autopan(beam, 0.3 * np.sin(2 * np.pi * 1.2 * tv(n))), 1)]
    parts += [(0.3 + k * 0.42, tone(hz(84 - k * 2), 0.15, tau=0.04), 0.25) for k in range(5)]
    parts += [(2.5, tone(hz(81), 0.8, tau=0.25), 0.35), (2.5, tone(hz(88), 0.8, tau=0.25), 0.3)]
    export(D10 + '生体スキャン', space(seq(parts), 0.5), -19)

    # cyberware OS boot: a deep swell, a glass arpeggio and a settled chord
    parts = [(0, sub(1.2, 30, 55, 0.6, 0.8), 0.4), (0, sweep(g, 1.0, 200, 5000, 0.95, 0.5), 0.6)]
    parts += [(0.9 + i * 0.07, tone(hz(m), 0.5, tau=0.12), 0.3, (-0.5, 0.5)[i % 2]) for i, m in enumerate([69, 73, 76, 81, 85, 88])]
    parts += [(1.35, pad(hz(57), 1.6, att=0.05, rel=1.2), 0.2), (1.35, pad(hz(64), 1.6, att=0.05, rel=1.2), 0.15),
              (1.35, tone(hz(93), 1.2, tau=0.5), 0.2)]
    export(D10 + '義体OS_起動', space(pingpong(seq(parts), 0.12, 0.2, 3), 0.7), -18)

    # system warning: a soft two-tone nag, not an alarm
    x = seq([(i * 0.5, tone(hz(m), 0.3, tau=0.1, partial=0.1), 0.45) for i, m in enumerate([76, 72, 76, 72])])
    export(D10 + '警告_注意', space(x, 0.4), -19)

    # news flash: a short bright sting with a drum-like sub hit
    parts = [(0, sub(0.5, 120, 45, 0.04), 0.7), (0, click(g, 0.5, 1500), 1)]
    parts += [(0.0 + i * 0.12, tone(hz(m), 0.6, tau=0.2, fm=0.6), 0.35) for i, m in enumerate([79, 84, 88])]
    parts += [(0.36, sub(0.5, 120, 45, 0.04), 0.7), (0.36, pad(hz(72), 1.6, att=0.01, rel=1.3), 0.2),
              (0.36, pad(hz(79), 1.6, att=0.01, rel=1.3), 0.15), (0.36, tone(hz(91), 1.6, tau=0.6), 0.3)]
    export(D10 + 'ニュース速報', space(pingpong(seq(parts), 0.15, 0.2, 2), 0.8), -16)

    # navigation start
    x = seq([(0, tone(hz(81), 0.4, tau=0.1), 0.4), (0.12, tone(hz(88), 0.4, tau=0.1), 0.4), (0.24, tone(hz(86), 0.7, tau=0.25), 0.4)])
    export(D10 + 'ナビ_案内開始', space(x), -19)


# ================================================================ 11 role gadgets (synth)
def role():
    g = Gen(5300)

    # solo: smartlink lock-on, three chirps tightening into a held lock tone
    parts = [(i * 0.13, tone(hz(86 + i * 3), 0.1, tau=0.03, partial=0.3), 0.35, (-0.4, 0.4, 0)[i]) for i in range(3)]
    parts += [(0.4, tone(hz(98), 0.5, tau=0.25, fm=0.3), 0.4), (0.4, tone(hz(86), 0.5, tau=0.25), 0.2)]
    export(D11 + 'ソロ_照準ロック', space(seq(parts), 0.3), -19)

    # solo: optical camo on (a shimmer that rises and thins out) / off (it falls back in)
    n = ns(1.6)
    sh = sum(np.sin(2 * np.pi * np.cumsum(np.full(n, f) * (1 + 0.004 * np.sin(2 * np.pi * g.u(3, 8) * tv(n)))) / SR)
             for f in (1300, 1950, 2600, 3900)) / 4
    on = seq([(0, sweep(g, 1.6, 400, 8000, 0.3, 0.5), 0.8), (0, sh * env_points(n, [(0, 0), (0.3, 1), (1.6, 0)]), 0.2),
              (0, grains(g, 1.4, 120, 3000, 11000, amp=0.08), 1), (0, sub(0.5, 100, 40, 0.05), 0.3)])
    export(D11 + 'ソロ_光学迷彩_起動', space(on, 0.6), -18)
    off = seq([(0, sweep(g, 1.0, 9000, 500, 0.75, 0.5), 0.8), (0, (sh * env_points(n, [(0, 0), (1.0, 1), (1.6, 0)]))[:ns(1.2)], 0.2),
               (0.9, sub(0.5, 90, 40, 0.06), 0.4), (0.9, click(g, 0.4, 1500), 1)])
    export(D11 + 'ソロ_光学迷彩_解除', space(off, 0.6), -18)

    # solo: sandevistan, a hard whoosh, the world drops an octave into a slow heartbeat, then snaps back (4 s)
    n = ns(3.0)
    drone = (pad(hz(33), 3.0, att=0.3, rel=0.4, detune=0.01) + 0.4 * pad(hz(45), 3.0, att=0.3, rel=0.4, detune=0.012))
    heart = np.zeros(n)
    for t0 in (0.5, 1.6, 2.6):
        heart = place(heart, sub(0.25, 70, 40, 0.05), t0, 0.9)
        heart = place(heart, sub(0.25, 60, 35, 0.05), t0 + 0.18, 0.6)
    parts = [(0, sweep(g, 0.4, 300, 9000, 0.15, 0.6), 1.0), (0, sub(0.6, 140, 30, 0.1), 0.8), (0, click(g, 0.8, 1000), 1),
             (0.2, drone, 0.35), (0.2, heart, 0.6), (0.2, grains(g, 2.8, 25, 400, 1600, glen=(0.05, 0.15), amp=0.1), 1),
             (3.2, sweep(g, 0.35, 9000, 300, 0.85, 0.6), 1.0), (3.5, sub(0.4, 50, 120, 0.05), 0.5), (3.52, click(g, 0.6, 2000), 1)]
    export(D11 + 'ソロ_加速装置', space(seq(parts), 1.2, 0.3), -15)

    # medtech: defibrillator, the charge whine, the ready beep, the shock
    n = ns(1.6)
    whine = np.sin(2 * np.pi * np.cumsum(np.linspace(600, 4200, n) ** 1.0) / SR) * np.linspace(0.1, 1, n)
    zap = seq([(0, sub(0.5, 90, 35, 0.06), 1), (0, sat(hp(g.r.standard_normal(ns(0.15)), 300) * env_ad(ns(0.15), 0.001, 0.03) * 2, 2), 0.6)])
    parts = [(0, lp(whine, 7000), 0.1), (1.65, tone(hz(93), 0.25, tau=0.08, partial=0.0), 0.35),
             (1.95, tone(hz(93), 0.25, tau=0.08, partial=0.0), 0.35), (2.4, zap, 1)]
    export(D11 + 'メドテック_除細動器', space(seq(parts), 0.5), -15)

    # medtech: air hypo, a short pressurised hiss and a seal click
    m = ns(0.35)
    hiss = bp(g.r.standard_normal(m), 3000, 12000) * env_ad(m, 0.002, 0.07)
    x = seq([(0, click(g, 0.5, 1500), 1), (0.03, hiss, 0.5), (0.03, sub(0.12, 200, 90, 0.02), 0.2), (0.32, tone(hz(91), 0.12, tau=0.03), 0.15)])
    export(D11 + 'メドテック_エアハイポ', space(x, 0.3, 0.12), -19)

    # media: record start / stop
    x = seq([(0, tone(hz(81), 0.2, tau=0.05), 0.4), (0.1, tone(hz(93), 0.4, tau=0.12), 0.4), (0.1, click(g, 0.3, 4000), 1)])
    export(D11 + 'メディア_録画開始', space(x, 0.3), -20)
    x = seq([(0, tone(hz(93), 0.2, tau=0.05), 0.4), (0.1, tone(hz(81), 0.4, tau=0.12), 0.4)])
    export(D11 + 'メディア_録画停止', space(x, 0.3), -20)

    # lawman: stun baton, a power-up hum and a crackling discharge
    n = ns(1.2)
    hum = (np.sin(2 * np.pi * 120 * tv(n)) + 0.5 * np.sin(2 * np.pi * 240 * tv(n)) + 0.3 * np.sign(np.sin(2 * np.pi * 120 * tv(n)))) * \
        env_points(n, [(0, 0), (0.2, 1), (1.2, 0.8)])
    crack = np.zeros(ns(0.8))
    for k in range(40):
        t0 = g.u(0, 0.7)
        m = ns(g.u(0.002, 0.012))
        crack = place(crack, hp(g.r.standard_normal(m), 2000) * g.u(0.3, 1), t0)
    crack *= env_points(len(crack), [(0, 1), (0.8, 0.3)])
    x = seq([(0, sweep(g, 0.3, 300, 3000, 0.9, 0.5), 0.4), (0, lp(hum, 3000), 0.15), (0.9, crack, 0.7), (0.9, sub(0.3, 120, 50, 0.04), 0.5)])
    export(D11 + 'ローマン_スタン警棒', space(x, 0.4), -16)

    # lawman: body camera on
    x = seq([(0, tone(hz(88), 0.15, tau=0.04), 0.4), (0.15, tone(hz(88), 0.15, tau=0.04), 0.4), (0.3, tone(hz(95), 0.4, tau=0.1), 0.35)])
    export(D11 + 'ローマン_ボディカメラ', space(x, 0.3), -20)

    # exec: contract signed, a calm two-chord confirmation
    x = seq([(0, pad(hz(64), 1.4, att=0.01, rel=1.1), 0.2), (0, pad(hz(71), 1.4, att=0.01, rel=1.1), 0.15),
             (0, tone(hz(88), 1.0, tau=0.3), 0.25), (0.25, tone(hz(95), 1.4, tau=0.5, fm=0.3), 0.3),
             (0.25, pad(hz(69), 1.6, att=0.01, rel=1.3), 0.2), (0.25, pad(hz(76), 1.6, att=0.01, rel=1.3), 0.15)])
    export(D11 + 'エグゼク_契約承認', space(pingpong(x, 0.16, 0.2, 2), 0.9), -19)

    # exec: holo-conference join, a shimmering resolve into presence
    x = seq([(0, sweep(g, 0.8, 300, 7000, 0.8, 0.5), 0.6), (0.1, grains(g, 0.8, 140, 2000, 9000, amp=0.1), 1),
             (0.7, tone(hz(76), 0.8, tau=0.3), 0.3), (0.75, tone(hz(83), 0.8, tau=0.3), 0.3), (0.8, tone(hz(88), 1.2, tau=0.4), 0.3)])
    export(D11 + 'エグゼク_ホロ会議', space(x, 0.6), -19)

    # fixer: encrypted line, a scrambler warble settling into a clean connect
    n = ns(1.2)
    war = np.sin(2 * np.pi * np.cumsum(1500 + 800 * np.sin(2 * np.pi * 9 * tv(n)) * np.linspace(1, 0, n)) / SR) * env_points(n, [(0, 0), (0.1, 1), (1.2, 0)])
    x = seq([(0, bitcrush(war, 6, 4), 0.15), (0, bp(g.r.standard_normal(n), 500, 4000) * env_points(n, [(0, 0.3), (1.0, 0.05), (1.2, 0)]), 0.12),
             (1.1, tone(hz(84), 0.4, tau=0.1), 0.35), (1.18, tone(hz(91), 0.6, tau=0.2), 0.35)])
    export(D11 + 'フィクサー_暗号回線', space(x, 0.4), -19)


# ================================================================ 07 loop
def loop():
    g = Gen(5400)
    # patient monitor: a soft sine beep at 72 bpm with a quiet pump breathing under it (16 beats, wraps)
    beat = 60 / 72
    L = beat * 20
    n = ns(L)
    buf = np.zeros((n, 2))
    for k in range(20):
        b = stereo(tone(hz(89), 0.25, tau=0.05, partial=0.05), 0.2) * 0.35
        i = ns(k * beat)
        e = min(n, i + len(b))
        buf[i:e] += b[:e - i]
        buf[:max(0, i + len(b) - n)] += b[e - i:]
    vent = np.zeros(n)
    per = L / 5
    for k in range(5):
        m = ns(per)
        v = bp(g.r.standard_normal(m), 300, 2500) * (np.sin(np.pi * np.linspace(0, 1, m)) ** 2)
        vent[ns(k * per):ns(k * per) + m] += v[:len(vent[ns(k * per):ns(k * per) + m])]
    hum = 0.02 * np.sin(2 * np.pi * 100 * tv(n))
    buf += stereo(vent * 0.025 + hum)
    ir = make_ir(Gen(3), rt60=0.4, predelay=0.01, lp_start=10000, lp_end=4000, tail_energy=0.4)
    # convolve three copies and keep the middle one: the reverb tail of the previous lap wraps in
    w = convolve(np.concatenate([buf, buf, buf]), ir)
    out = buf + 0.2 * w[n:2 * n]
    export(D7 + 'メドテック_生体モニター', out, -26, loop=True, ogg=True)


if __name__ == '__main__':
    which = sys.argv[1:] or ['hack', 'ui', 'role', 'loop']
    for w in which:
        {'hack': hack, 'ui': ui, 'role': role, 'loop': loop}[w]()
