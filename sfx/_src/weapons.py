"""Gunshot / weapon building blocks."""
import numpy as np

from dsp import (SR, Gen, ns, tvec, lp, hp, bp, peak, shelf_low, env_exp, env_ad,
                 sweep_sine, modal, metal_modes, sat, compress, make_ir, convolve,
                 stereo, block_filter, crackle, place)


# ------------------------------------------------------------ spaces
def street_ir(g, size=1.0, rt60=2.4):
    """Urban street canyon: distinct building slapbacks then a long rolling tail."""
    early = []
    t = 0.028 * size
    gain = 0.42
    lpf = 9000
    for i in range(9):
        early.append((t, gain, lpf))
        t += g.u(0.025, 0.07) * size
        gain *= g.u(0.66, 0.82)
        lpf *= 0.8
    return make_ir(g, rt60=rt60, predelay=0.03 * size, early=early, lp_start=6000,
                   lp_end=900, low_rt_mult=1.25, tail_energy=0.35 * size, low_amt=0.7)


def indoor_ir(g, rt60=0.75):
    early = [(g.u(0.003, 0.025), g.u(0.25, 0.5), 10000) for _ in range(10)]
    return make_ir(g, rt60=rt60, predelay=0.004, early=early, lp_start=11000, lp_end=2500,
                   low_rt_mult=1.1, tail_energy=0.8)


def hall_ir(g, rt60=3.2):
    """Big concrete space: warehouse / parking garage."""
    early = [(g.u(0.01, 0.08), g.u(0.2, 0.45), 7000) for _ in range(14)]
    return make_ir(g, rt60=rt60, predelay=0.012, early=early, lp_start=8000, lp_end=1500,
                   low_rt_mult=1.15, tail_energy=1.6)


# ------------------------------------------------------------ gunshot core
def gunshot(g, cal=1.0, bright=1.0, boom=1.0, length=0.6, crack=1.0, ring=1.0, snap=1.0):
    """Dry gunshot (mono).

    cal: overall size (pistol 0.8, rifle 1.0, shotgun 1.3, sniper 1.6)
    """
    n = ns(length)
    t = tvec(n)
    y = np.zeros(n)

    # 1) N-wave muzzle shock + very short broadband burst
    nd = max(8, ns(0.00035 * cal))
    nw = np.linspace(1, -0.8, nd)
    y[:nd] += nw * 1.4 * crack
    burst = g.r.standard_normal(n) * env_ad(n, 0.00008, 0.0018 * cal)
    y += hp(burst, 900) * 1.3 * crack * snap

    # 2) blast: noise whose cutoff collapses quickly (pshhh)
    blast = g.r.standard_normal(n)
    fc = 1400 + 9000 * bright * np.exp(-t / (0.012 * cal))
    blast = block_filter(blast, fc, 'lowpass', order=2, block=64)
    y += blast * env_ad(n, 0.0002, 0.018 * cal) * 2.4

    # 3) gas body: pinkish mid punch
    mid = bp(g.r.standard_normal(n), 280 / cal ** 0.3, 2400 / cal ** 0.3)
    y += mid * env_ad(n, 0.0004, 0.03 * cal) * 2.6

    # 4) low thump (pressure wave in the body)
    th = sweep_sine(n, 170 / cal ** 0.3, 42 / cal ** 0.2, 0.03 * cal, harmonics=[(2, 0.25)])
    y += th * env_ad(n, 0.0012, 0.06 * cal ** 1.3) * 0.6 * boom

    # 5) metallic ring (receiver / barrel)
    if ring > 0:
        mm = metal_modes(g, g.u(1500, 2100), count=10, tau=0.05, bright=0.85)
        y += modal(n, mm) * 0.06 * ring

    # punch it like a real (clipped) field recording
    y = sat(y * 1.2, 2.6)
    y = peak(y, 110, 0.9, 2)
    y = peak(y, 450, 0.8, 3.5)
    y = peak(y, 3500, 1.2, 2 * bright)
    return y


def mech_click(g, f0=3200, amp=1.0, tau=0.012, count=8, noise=0.6):
    """Short metal-on-metal click (slide, bolt, hammer)."""
    n = ns(0.12)
    mm = metal_modes(g, f0 * g.u(0.9, 1.1), count=count, tau=tau, bright=0.9)
    y = modal(n, mm)
    nz = hp(g.r.standard_normal(n), 2000) * env_ad(n, 0.0001, 0.0025)
    y = y * 0.5 + nz * noise
    y = sat(y, 1.5)
    return y * amp


def thunk(g, f=180, tau=0.04, amp=1.0):
    """Low knock of metal parts seating (mag insert, slide home)."""
    n = ns(0.25)
    y = sweep_sine(n, f * 1.6, f, 0.01) * env_ad(n, 0.0005, tau)
    y += lp(g.r.standard_normal(n), 2500) * env_ad(n, 0.0002, 0.006) * 0.7
    return y * amp


def shell_drop(g, start=0.0, count=1, surface='concrete', length=1.6, pan=0.4):
    """Brass casings bouncing on the floor (stereo)."""
    out = np.zeros((ns(start + length), 2))
    for c in range(count):
        t0 = start + c * g.u(0.05, 0.11) + g.u(0, 0.03)
        p = np.clip(pan + g.u(-0.4, 0.4), -1, 1)
        h = g.u(0.6, 1.0)
        dt = g.u(0.09, 0.14)
        tt = t0
        f0 = g.u(4800, 6400)
        for b in range(6):
            n = ns(0.3)
            modes = [(f0 * r * g.u(0.99, 1.01), g.u(0.03, 0.09) * (0.8 ** b), a)
                     for r, a in [(1, 1), (2.76, 0.6), (5.4, 0.35), (1.53, 0.4), (8.9, 0.15)]]
            hit = modal(n, modes) + hp(g.r.standard_normal(n), 3000) * env_exp(n, 0.0008) * 0.6
            if surface == 'concrete':
                hit += bp(g.r.standard_normal(n), 800, 4000) * env_exp(n, 0.002) * 0.4
            out = place(out, stereo(hit * h, p), tt) if ns(tt) < len(out) else out
            tt += dt
            dt *= g.u(0.55, 0.75)
            h *= g.u(0.45, 0.7)
            if dt < 0.008:
                break
        # final little rolling tinkle
        roll_n = ns(0.25)
        roll = crackle(g, roll_n, np.linspace(400, 0, roll_n), tau=0.0003, lo=3500, hi=14000)
        out = place(out, stereo(roll * 0.15 * h, p), tt) if ns(tt) < len(out) else out
    return out * 0.5


def whoosh(g, dur, f_lo, f_hi, peak_at=0.5, width=0.6, amp=1.0, order=2):
    n = ns(dur)
    t = tvec(n) / dur
    curve = np.where(t < peak_at, t / peak_at, (1 - t) / (1 - peak_at))
    fc = f_lo + (f_hi - f_lo) * curve
    y = block_filter(g.r.standard_normal(n), fc, 'bandpass', order=order, block=128, width=None)
    e = np.sin(np.pi * np.clip(t, 0, 1)) ** 2 * (0.3 + 0.7 * curve)
    return y * e * amp


def place_shots(g, times, maker, length):
    out = np.zeros(ns(length))
    for t0 in times:
        s = maker(g)
        i = ns(t0)
        e = min(len(out), i + len(s))
        out[i:e] += s[:e - i]
    return out


def space(dry, ir, wet=1.0, dry_gain=1.0, pre_lp=None, width=0.15):
    """dry (mono or stereo) through ir, returns stereo."""
    src = dry if pre_lp is None else lp(dry, pre_lp)
    w = convolve(src, ir)
    d = stereo(dry) if dry.ndim == 1 else dry
    out = np.zeros((max(len(w), len(d)), 2))
    out[:len(d)] += d * dry_gain
    # add a hint of width to the direct sound via tiny Haas on a high band
    if width > 0 and dry.ndim == 1:
        hi = hp(dry, 2500) * width
        k = ns(0.0006)
        out[k:k + len(hi), 1] += hi
        out[:len(hi), 0] -= hi * 0.5
    out[:len(w)] += w * wet
    return out


def electric_arc(g, dur, intensity=1.0, hum=True):
    n = ns(dur)
    t = tvec(n)
    dens = 900 * intensity * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * g.u(3, 9) * t)))
    y = crackle(g, n, dens, tau=0.00025, lo=1200, hi=16000) * 2.5
    buzz = bp(g.r.standard_normal(n), 2500, 9000) * (0.4 + 0.6 * (g.r.random(n) < 0.02).astype(float))
    y += lp(buzz, 9000) * 0.3
    if hum:
        f = 120 + 2 * np.sin(2 * np.pi * 0.7 * t)
        h = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.5
        h = bp(h, 100, 3000)
        y += h * 0.25 * intensity
    return sat(y, 1.8)
