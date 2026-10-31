"""04_近接 / 05_ハッキング / 06_機械・乗り物"""
import numpy as np

from dsp import (SR, Gen, ns, tvec, lp, hp, bp, peak, env_exp, env_ad, env_points, sweep_sine,
                 modal, metal_modes, sat, stereo, place, osc, block_filter, crackle, autopan,
                 bitcrush, doppler, make_ir, fade)
from master import export
from weapons import (mech_click, thunk, whoosh, street_ir, indoor_ir, hall_ir, space, electric_arc)
from gen_hits import flesh_hit, metal_hit, close_room

D4 = '04_近接/'
D5 = '05_ハッキング/'
D6 = '06_機械・乗り物/'


def fm_bell(n, fc, ratio=1.4, index=3.0, tau=0.6, att=0.002):
    t = tvec(n)
    env = env_ad(n, att, tau)
    idx = index * env_exp(n, tau * 0.5)
    return np.sin(2 * np.pi * fc * t + idx * np.sin(2 * np.pi * fc * ratio * t)) * env


def blip(n, f, shape='square', tau=0.02, att=0.001, cutoff=7000):
    y = osc(f, n, shape)
    return lp(y, cutoff) * env_ad(n, att, tau)


def digital_space(g):
    return make_ir(g, rt60=1.4, predelay=0.02, early=[(0.06, 0.3, 8000), (0.12, 0.2, 6000), (0.18, 0.12, 5000)],
                   lp_start=12000, lp_end=5000, tail_energy=0.7)


# ================================================================ 04 melee
def blade_ring(g, dur=4.0, f0=2350, amp=1.0):
    n = ns(dur)
    modes = [(f0 * r, tau, a) for r, tau, a in
             [(1, 0.9, 1), (1.003, 0.85, 0.7), (2.71, 0.5, 0.5), (4.13, 0.35, 0.3), (5.9, 0.2, 0.2), (0.43, 0.4, 0.25)]]
    y = modal(n, modes)
    beat = 1 + 0.15 * np.sin(2 * np.pi * 5.5 * tvec(n))
    return fade(y * beat * amp, 0, 0.3)


def katana_draw():
    g = Gen(401)
    L = 4.6
    n = ns(0.55)
    t = tvec(n)
    # steel sliding out of the scabbard: resonant scrape rising in pitch
    fc = 1800 + 4200 * (t / 0.55) ** 1.4
    scrape = block_filter(g.r.standard_normal(n), fc, 'bandpass', order=2, width=900)
    grit = crackle(g, n, 2500, tau=0.0002, lo=2000, hi=12000) * 0.5
    scrape = (scrape + grit) * env_points(n, [(0, 0), (0.08, 0.5), (0.45, 1), (0.55, 0)])
    out = np.zeros((ns(L), 2))
    out = place(out, stereo(scrape * 0.6, -0.1), 0)
    out = place(out, stereo(mech_click(g, 3100, 0.5, 0.01), 0), 0.0)  # habaki leaving the koiguchi
    out = place(out, stereo(blade_ring(g, 4.0, 2350, 0.35), 0.15), 0.52)
    out = place(out, autopan(whoosh(g, 0.3, 500, 2600, peak_at=0.4, amp=0.5), np.linspace(-0.3, 0.5, ns(0.3))), 0.5)
    out = space(out, indoor_ir(g, 0.6), wet=0.4)
    export(D4 + '刀_抜刀', out, -17)


def swing_whoosh(g, dur=0.38, lo=300, hi=2200, amp=1.0):
    y = whoosh(g, dur, lo, hi, peak_at=0.55, amp=amp)
    # thin blade adds a narrow whistle on top
    n = len(y)
    t = tvec(n) / dur
    curve = np.where(t < 0.55, t / 0.55, (1 - t) / 0.45)
    wh = block_filter(g.r.standard_normal(n), 1800 + 2500 * curve, 'bandpass', order=2, width=250)
    return y + wh * np.sin(np.pi * np.clip(t, 0, 1)) ** 3 * amp * 0.6


def blade_swings():
    g = Gen(402)
    out = np.zeros((ns(1.4), 2))
    out = place(out, autopan(swing_whoosh(g), np.linspace(-0.7, 0.7, ns(0.38))), 0)
    out = place(out, autopan(swing_whoosh(g, 0.3, 350, 2600, 0.9), np.linspace(0.7, -0.6, ns(0.3))), 0.5)
    out = space(out, indoor_ir(g, 0.5), wet=0.3)
    export(D4 + '斬撃_空振り', out, -17)


def blade_hit():
    g = Gen(403)
    out = np.zeros((ns(4.2), 2))
    out = place(out, autopan(swing_whoosh(g, 0.3), np.linspace(-0.6, 0.2, ns(0.3))), 0)
    n = ns(0.6)
    slice_ = hp(g.r.standard_normal(n), 2500) * env_ad(n, 0.0005, 0.025) * 0.9  # the cut itself
    cut = flesh_hit(g, 0.8, wet=1.3) * 0.8 + slice_
    out = place(out, stereo(cut, 0.1), 0.2)
    out = place(out, stereo(blade_ring(g, 4.0, 2600, 0.1), 0.2), 0.21)
    out = space(out, close_room(g), wet=0.6)
    export(D4 + '斬撃_命中', out, -15, max_gr=6)


def servo(g, dur, f0, f1, amp=1.0):
    n = ns(dur)
    t = tvec(n)
    f = f0 + (f1 - f0) * np.clip(t / dur, 0, 1) ** 0.7
    y = osc(f, n, 'saw') * 0.6 + osc(f * 2, n, 'sine') * 0.3
    y = lp(y, 4000) + bp(g.r.standard_normal(n), 1500, 6000) * 0.08
    y *= env_points(n, [(0, 0), (0.02, 1), (dur - 0.03, 0.8), (dur, 0)])
    return y * amp


def arm_blade():
    """Forearm blade deploys: servo, latches unlocking, blades snap out and ring."""
    g = Gen(404)
    out = np.zeros((ns(4.6), 2))
    out = place(out, stereo(servo(g, 0.35, 260, 820, 0.35), -0.2), 0.0)
    for k, t0 in enumerate([0.05, 0.14, 0.22]):
        out = place(out, stereo(mech_click(g, 2600 + k * 400, 0.5, 0.01), -0.2 + 0.1 * k), t0)
    hn = ns(0.3)
    hiss = bp(g.r.standard_normal(hn), 2500, 10000) * env_ad(hn, 0.005, 0.08)
    out = place(out, stereo(hiss * 0.4, 0.2), 0.33)
    out = place(out, stereo(thunk(g, 140, 0.05, 0.9), 0), 0.38)
    out = place(out, stereo(mech_click(g, 2200, 0.9, 0.02, noise=0.9), 0), 0.38)
    out = place(out, stereo(blade_ring(g, 4.0, 1950, 0.3), -0.4), 0.39)
    out = place(out, stereo(blade_ring(g, 4.0, 2080, 0.3), 0.4), 0.405)
    out = space(out, indoor_ir(g, 0.6), wet=0.35)
    export(D4 + 'アームブレード展開', out, -15)


def punch_core(g, size=1.0):
    n = ns(0.5)
    t = tvec(n)
    slap = bp(g.r.standard_normal(n), 1200, 6000) * env_ad(n, 0.0002, 0.004) * 1.2
    body = sweep_sine(n, 180 * g.u(0.9, 1.1), 55, 0.02) * env_ad(n, 0.001, 0.06 * size) * 1.6
    body += lp(g.r.standard_normal(n), 600) * env_ad(n, 0.001, 0.025) * 0.8
    return sat(slap + body, 2.0)


def punches():
    g = Gen(405)
    out = np.zeros((ns(1.3), 2))
    for k, (t0, pan) in enumerate([(0.0, -0.3), (0.42, 0.3)]):
        out = place(out, autopan(whoosh(g, 0.15, 400, 1800, 0.8, amp=0.4), np.linspace(-pan, pan, ns(0.15))), t0)
        out = place(out, stereo(punch_core(g, 1.0 + 0.2 * k), pan * 0.5), t0 + 0.13)
    out = space(out, close_room(g), wet=0.6)
    export(D4 + '打撃_パンチ', out, -15)


def cyber_punch():
    """Heavy cybernetic arm: hydraulic wind-up, crushing hit, metal and pistons."""
    g = Gen(406)
    out = np.zeros((ns(2.0), 2))
    out = place(out, stereo(servo(g, 0.3, 120, 260, 0.3), 0), 0.0)
    hn = ns(0.25)
    hyd = bp(g.r.standard_normal(hn), 800, 5000) * env_points(hn, [(0, 0), (0.18, 0.6), (0.25, 0)])
    out = place(out, stereo(hyd * 0.5, 0), 0.05)
    out = place(out, autopan(whoosh(g, 0.2, 200, 1400, 0.85, amp=0.6), np.linspace(-0.4, 0.2, ns(0.2))), 0.12)
    hit = punch_core(g, 1.8)
    hit[:ns(0.5)] += sweep_sine(ns(0.5), 110, 35, 0.04) * env_ad(ns(0.5), 0.002, 0.12) * 1.4
    hit = sat(hit, 1.4)
    out = place(out, stereo(hit, 0.1), 0.3)
    out = place(out, stereo(metal_hit(g, 520, 0.12, 0.35, bright=0.8), 0.1), 0.3)
    out = place(out, stereo(flesh_hit(g, 1.2, bone=0.9) * 0.6, 0.1), 0.302)
    # piston release
    rn = ns(0.4)
    rel = bp(g.r.standard_normal(rn), 2000, 9000) * env_ad(rn, 0.01, 0.1)
    out = place(out, stereo(rel * 0.35, -0.2), 0.48)
    out = place(out, stereo(mech_click(g, 2100, 0.4, 0.02), -0.2), 0.47)
    out = space(out, close_room(g), wet=0.7)
    export(D4 + '打撃_サイバーアーム', out, -14)


# ================================================================ 05 hacking
def data_chirps(g, dur, rate=40, f_lo=900, f_hi=5200, rising=0.0, crush=True):
    n = ns(dur)
    y = np.zeros(n)
    t0 = 0.0
    while t0 < dur:
        k = ns(g.u(0.008, 0.03))
        prog = t0 / dur
        lo = f_lo * (1 + rising * prog)
        f = g.u(lo, f_hi * (1 + rising * prog))
        b = blip(k, f, 'square' if g.u() > 0.4 else 'sine', tau=k / SR * 0.6, cutoff=9000)
        y = place(y, b * g.u(0.3, 1.0), t0)
        t0 += 1 / rate * g.u(0.5, 1.5)
    if crush:
        y = bitcrush(y, 7, 2)
    return y


def jack_in():
    g = Gen(501)
    L = 4.2
    out = np.zeros((ns(L + 1.5), 2))
    # physical plug in the neck port
    out = place(out, stereo(mech_click(g, 2800, 0.6, 0.012), 0), 0.0)
    out = place(out, stereo(thunk(g, 260, 0.02, 0.4), 0), 0.0)
    # sync tones
    for k, f in enumerate([523.25, 783.99, 1046.5]):
        b = fm_bell(ns(0.5), f, 2.0, 1.2, 0.18) * 0.18
        out = place(out, stereo(b, (k - 1) * 0.4), 0.25 + k * 0.11)
    # rising data stream
    n = ns(2.2)
    t = tvec(n)
    ch = data_chirps(g, 2.2, 55, 700, 3000, rising=1.5) * (t / 2.2) ** 1.2 * 0.5
    f = 120 * (2400 / 120) ** ((t / 2.2) ** 2)
    rise = (osc(f, n, 'saw') * 0.3 + osc(f * 1.007, n, 'saw') * 0.3)
    rise = block_filter(rise, 400 + f * 2, 'lowpass') * (t / 2.2) ** 2 * 0.5
    out = place(out, autopan(ch, 0.6 * np.sin(2 * np.pi * 1.3 * t)), 0.6)
    out = place(out, stereo(rise, 0), 0.6)
    # dive: whoosh down into netspace + sub drop + shimmering tail
    m = ns(2.0)
    tt = tvec(m)
    dive = block_filter(g.r.standard_normal(m), 9000 * np.exp(-tt / 0.35) + 150, 'lowpass') * env_ad(m, 0.005, 0.6)
    sub = sweep_sine(m, 160, 40, 0.15) * env_ad(m, 0.01, 0.8) * 0.8
    shimmer = sum(osc(fr, m, 'sine') * env_ad(m, 0.05, 0.9) * 0.05 for fr in [1567.98, 2093.0, 2637.0, 3135.96])
    out = place(out, stereo(dive * 0.7 + sub, 0), 2.8)
    out = place(out, np.stack([shimmer, np.roll(shimmer, ns(0.011))], 1), 2.85)
    out = space(out, digital_space(g), wet=0.8)
    export(D5 + 'ジャックイン', out, -15)


def quickhack():
    g = Gen(502)
    out = np.zeros((ns(2.4), 2))
    n = ns(0.9)
    t = tvec(n)
    ch = data_chirps(g, 0.9, 70, 1200, 4500, rising=1.0) * env_points(n, [(0, 0.3), (0.8, 1), (0.9, 0.6)])
    out = place(out, autopan(ch * 0.5, 0.5 * np.sin(2 * np.pi * 3 * t)), 0)
    # charging tone
    f = 300 * (1800 / 300) ** (t / 0.9)
    tone = osc(f, n, 'square') * 0.15
    tone = block_filter(tone, 800 + f * 3, 'lowpass') * (t / 0.9)
    out = place(out, stereo(bitcrush(tone, 6, 2), 0), 0)
    # send: a zip that leaves to the right and a punchy digital hit
    m = ns(0.35)
    tt = tvec(m)
    zf = 600 + 7000 * (tt / 0.35) ** 2
    zip_ = osc(zf, m, 'saw') * env_ad(m, 0.002, 0.12) * 0.25
    zip_ = lp(zip_, 12000)
    out = place(out, autopan(zip_, np.linspace(0, 0.9, m)), 0.9)
    k = ns(0.5)
    hit = sweep_sine(k, 300, 55, 0.03) * env_ad(k, 0.001, 0.1) * 0.9
    hit += bitcrush(hp(g.r.standard_normal(k), 1000) * env_ad(k, 0.0005, 0.02), 5, 4) * 0.5
    out = place(out, stereo(hit, 0.3), 0.92)
    out = space(out, digital_space(g), wet=0.5)
    export(D5 + 'クイックハック送信', out, -15)


def access_granted():
    g = Gen(503)
    out = np.zeros((ns(2.0), 2))
    for k, (t0, f) in enumerate([(0.0, 880.0), (0.1, 1318.5), (0.2, 1760.0)]):
        b = fm_bell(ns(1.2), f, 2.0, 1.5, 0.35) * 0.3 + osc(f, ns(1.2), 'tri') * env_ad(ns(1.2), 0.003, 0.15) * 0.1
        out = place(out, stereo(b, (k - 1) * 0.3), t0)
    out = place(out, stereo(mech_click(g, 2600, 0.25, 0.01), 0), 0.0)
    out = space(out, digital_space(g), wet=0.5)
    export(D5 + 'アクセス許可', out, -17)


def access_denied():
    g = Gen(504)
    out = np.zeros((ns(1.4), 2))
    for k, (t0, f) in enumerate([(0.0, 220.0), (0.2, 165.0)]):
        n = ns(0.24)
        y = (osc(f, n, 'square') + osc(f * 1.01, n, 'saw')) * 0.3
        y = lp(y, 3500) * env_points(n, [(0, 0), (0.005, 1), (0.2, 0.8), (0.24, 0)])
        y = bitcrush(y, 6, 3)
        out = place(out, stereo(y, 0), t0)
    out = space(out, digital_space(g), wet=0.35)
    export(D5 + 'アクセス拒否', out, -17)


def ice_alert():
    """ICE countermeasure triggered: hostile, glitchy warning."""
    g = Gen(505)
    L = 3.6
    n = ns(L)
    t = tvec(n)
    seq = np.zeros(n)
    for k in range(8):
        m = ns(0.18)
        f = 988 if k % 2 == 0 else 740
        y = osc(f, m, 'square') * 0.35 + osc(f * 0.5, m, 'saw') * 0.25
        y = lp(y, 6000) * env_points(m, [(0, 0), (0.004, 1), (0.16, 0.9), (0.18, 0)])
        seq = place(seq, y, k * 0.22)
    # distortion stutters
    seq = sat(seq * 2, 2)
    gl = data_chirps(g, L, 25, 200, 8000) * 0.3
    seq = seq + gl
    # final lock: low buzz
    m = ns(1.2)
    buzz = osc(55, m, 'saw') * 0.6 + osc(110.7, m, 'square') * 0.3
    buzz = lp(buzz, 1800) * env_points(m, [(0, 0), (0.01, 1), (1.0, 0.8), (1.2, 0)])
    seq = place(seq, bitcrush(buzz, 5, 4), 1.85)
    out = space(seq, digital_space(g), wet=0.5)
    export(D5 + 'ICE検知_警告', out, -14)


def facility_alarm():
    """Corporate facility lockdown klaxon (good for the SFX repeat button)."""
    g = Gen(506)
    L = 6.0
    n = ns(L)
    t = tvec(n)
    period = 1.5
    ph = (t % period) / period
    f = 420 + 300 * np.sin(np.pi * np.clip(ph / 0.8, 0, 1)) ** 1.2
    y = osc(f, n, 'saw') * 0.5 + osc(f * 1.5, n, 'square') * 0.15
    y = lp(y, 3000) * (0.7 + 0.3 * (ph < 0.8))
    y = peak(y, 1200, 1.0, 5)
    y *= env_points(n, [(0, 0), (0.05, 1), (L - 0.3, 1), (L, 0)])
    out = space(lp(y, 2500), hall_ir(g, 2.4), wet=1.4, dry_gain=0.6)
    export(D5 + '警報_施設ロックダウン', out, -17)


def short_circuit():
    g = Gen(507)
    L = 2.4
    n = ns(L)
    arc = electric_arc(g, L, 1.6) * env_points(n, [(0, 0), (0.01, 1), (0.6, 0.9), (1.2, 0.3), (2.4, 0)])
    bang = sweep_sine(n, 400, 80, 0.02) * env_ad(n, 0.0005, 0.04) * 1.2
    bang += hp(g.r.standard_normal(n), 1500) * env_ad(n, 0.0001, 0.006)
    y = arc + bang
    out = space(y, indoor_ir(g, 0.8), wet=0.6)
    export(D5 + 'ショート_感電', out, -14)


def glitch():
    """System failure: stuttering buffer repeats, bit-rot, dropouts."""
    g = Gen(508)
    L = 2.6
    src_n = ns(L)
    t = tvec(src_n)
    src = (osc(220 * (1 + 0.5 * np.sin(2 * np.pi * 0.7 * t)), src_n, 'saw') * 0.3 +
           data_chirps(g, L, 40, 400, 6000) * 0.6)
    out = np.zeros(src_n)
    pos = 0
    i = 0
    while i < src_n:
        seg = ns(g.u(0.02, 0.12))
        mode = g.u()
        if mode < 0.35:  # stutter: repeat a tiny slice
            sl = ns(g.u(0.008, 0.03))
            chunk = np.tile(src[pos:pos + sl], int(np.ceil(seg / max(sl, 1))))[:seg]
        elif mode < 0.5:  # dropout
            chunk = np.zeros(seg)
        elif mode < 0.7:  # pitch-down tape stop on the slice
            idx = np.cumsum(np.linspace(1, 0.2, seg))
            chunk = np.interp(pos + idx, np.arange(src_n), src)
        else:
            chunk = bitcrush(src[pos:pos + seg], int(g.u(3, 7)), int(g.u(2, 9)))
        chunk = np.pad(chunk, (0, max(0, seg - len(chunk))))
        out[i:i + seg] = chunk[:src_n - i]
        i += seg
        pos = min(src_n - 1, pos + int(seg * g.u(0.5, 2)))
    out = sat(out * 1.5, 1.5)
    out = space(out, digital_space(g), wet=0.3)
    export(D5 + 'システム異常_グリッチ', out, -15)


def flatline():
    g = Gen(509)
    out = np.zeros((ns(9.0), 2))
    # heartbeat monitor: three beats, faster and weaker, then the flat tone
    for k, (t0, a) in enumerate([(0.0, 1), (0.85, 0.9), (1.55, 0.8), (2.1, 0.7)]):
        m = ns(0.12)
        b = osc(1000, m, 'sine') * env_points(m, [(0, 0), (0.004, 1), (0.1, 1), (0.12, 0)]) * 0.35 * a
        out = place(out, stereo(b, 0), t0)
    m = ns(5.0)
    flat = osc(1000, m, 'sine') * env_points(m, [(0, 0), (0.004, 1), (4.4, 1), (5.0, 0)]) * 0.35
    out = place(out, stereo(flat, 0), 2.7)
    # a brief glitch as the cyberdeck lets go
    gl = data_chirps(g, 0.6, 50, 300, 5000) * env_points(ns(0.6), [(0, 1), (0.6, 0)]) * 0.35
    out = place(out, stereo(gl, 0), 2.45)
    out = space(out, indoor_ir(g, 0.5), wet=0.25)
    export(D5 + 'フラットライン', out, -18)


def scan():
    g = Gen(510)
    L = 2.4
    n = ns(L)
    t = tvec(n)
    sweep = (t / L)
    f = 600 + 2600 * np.sin(np.pi * sweep) ** 2
    y = osc(f, n, 'sine') * 0.25 + osc(f * 1.5, n, 'sine') * 0.1
    y *= 0.6 + 0.4 * np.sin(2 * np.pi * 18 * t) ** 2
    y *= env_points(n, [(0, 0), (0.1, 1), (L - 0.3, 1), (L, 0)])
    beeps = np.zeros(n)
    for k, t0 in enumerate([0.4, 0.9, 1.4, 1.9]):
        beeps = place(beeps, blip(ns(0.05), 2400 + 200 * k, 'sine', 0.02) * 0.4, t0)
    out = autopan(y, np.sin(2 * np.pi * sweep) * 0.7)
    out = place(out, stereo(beeps, 0), 0)
    out = space(out, digital_space(g), wet=0.6)
    export(D5 + 'スキャン', out, -18)


def door_unlock():
    g = Gen(511)
    out = np.zeros((ns(2.4), 2))
    for k, (t0, f) in enumerate([(0.0, 1318.5), (0.16, 1174.7), (0.32, 1568.0), (0.48, 1396.9)]):
        out = place(out, stereo(blip(ns(0.08), f, 'square', 0.03, cutoff=5000) * 0.25, 0), t0)
    out = place(out, stereo(fm_bell(ns(0.6), 1760, 2.0, 0.8, 0.12) * 0.25, 0), 0.75)
    out = place(out, stereo(thunk(g, 150, 0.05, 0.9), 0), 0.95)
    out = place(out, stereo(mech_click(g, 1900, 0.8, 0.025, noise=0.7), 0), 0.95)
    out = place(out, stereo(mech_click(g, 2600, 0.4, 0.02), 0), 1.05)
    out = space(out, indoor_ir(g, 0.7), wet=0.5)
    export(D5 + '電子ロック解除', out, -18)


# ================================================================ 06 machines & vehicles
def auto_door():
    g = Gen(601)
    out = np.zeros((ns(2.6), 2))
    hn = ns(0.6)
    hiss = bp(g.r.standard_normal(hn), 1500, 9000) * env_ad(hn, 0.005, 0.15)
    out = place(out, stereo(hiss * 0.5, 0), 0)
    out = place(out, stereo(thunk(g, 120, 0.04, 0.6), 0), 0.0)
    sn = ns(0.9)
    slide = servo(g, 0.9, 180, 140, 0.25)
    roll = lp(g.r.standard_normal(sn), 900) * env_points(sn, [(0, 0), (0.1, 1), (0.8, 1), (0.9, 0)]) * 0.25
    out = place(out, autopan(slide + roll, np.linspace(-0.2, 0.7, sn)), 0.08)
    out = place(out, stereo(thunk(g, 95, 0.08, 1.0), 0.7), 0.98)
    out = place(out, stereo(mech_click(g, 1500, 0.4, 0.03), 0.7), 0.98)
    out = space(out, indoor_ir(g, 0.8), wet=0.6)
    export(D6 + '自動ドア_開', out, -18)


def flyby(src, dur, speed, closest, t_close, height=0.0, pan_dir=1):
    n = len(src)
    t = tvec(n)
    x = (t - t_close) * speed
    d = np.sqrt(x ** 2 + closest ** 2 + height ** 2)
    # the doppler read needs source material from *before* t=0 and after the end:
    # extend the (stationary) source by mirroring it at both ends
    pre = ns(np.max(d) / 343.0) + 16
    ext = np.concatenate([src[pre:0:-1], src, src[-2:-pre - 2:-1]])
    delay = d / 343.0 * SR
    y = np.interp(np.arange(n) + pre - delay, np.arange(len(ext)), ext) / np.maximum(d, 1.0)
    # air absorption: farther == duller
    near = np.clip(1 - (d - closest) / 120, 0, 1)
    y = lp(y, 2000) * (1 - near) + y * near
    y = fade(y, 1.2, 1.2)
    pan = np.clip(x / (closest * 2.5), -1, 1) * pan_dir
    return autopan(y * closest, pan)


def drone():
    g = Gen(602)
    L = 9.0
    n = ns(L)
    t = tvec(n)
    src = np.zeros(n)
    for k, bpf in enumerate([182, 191, 203, 214]):  # four rotors, blade-pass freq
        f = bpf * (1 + 0.01 * np.sin(2 * np.pi * g.u(0.3, 0.8) * t + k))
        r = osc(f, n, 'saw') * 0.5 + osc(f * 2, n, 'sine') * 0.2
        src += lp(r, 5000)
    src += bp(g.r.standard_normal(n), 300, 6000) * 0.3
    motor = osc(1450 + 30 * np.sin(2 * np.pi * 0.5 * t), n, 'sine') * 0.06
    src += motor
    y = flyby(src, L, 9.0, 4.0, 4.5, 3.0)
    out = space(y, street_ir(g, 1.0, 1.8), wet=0.35)
    export(D6 + 'ドローン通過', out, -18)


def av_flyby():
    """Flying car (AV) passing overhead: turbine whine + jet roar with doppler."""
    g = Gen(603)
    L = 10.0
    n = ns(L)
    t = tvec(n)
    whine = (osc(3300, n, 'sine') * 0.25 + osc(5150, n, 'sine') * 0.12 + osc(6600, n, 'sine') * 0.08 +
             osc(1650, n, 'sine') * 0.15)
    whine *= 1 + 0.05 * np.sin(2 * np.pi * 37 * t)
    roar = lp(g.r.standard_normal(n), 3500) * 0.9 + lp(g.brown(L), 300) * 0.8
    hum = osc(62, n, 'saw') * 0.2  # mag-lift field
    src = whine + roar + lp(hum, 400)
    y = flyby(src, L, 45.0, 18.0, 5.0, 10.0, pan_dir=-1)
    out = space(y, street_ir(g, 1.5, 3.0), wet=0.7)
    export(D6 + 'AV飛行車_通過', out, -16)


def siren_pass():
    g = Gen(604)
    L = 12.0
    n = ns(L)
    t = tvec(n)
    # wail: slow sweep up/down
    ph = (t % 3.2) / 3.2
    f = 620 + 680 * np.sin(np.pi * ph) ** 1.5
    siren = osc(f, n, 'square') * 0.4 + osc(f * 2, n, 'saw') * 0.15
    siren = bp(siren, 400, 4000)
    siren = peak(siren, 1500, 1.2, 4)
    engine = lp(osc(48 + 6 * np.sin(2 * np.pi * 0.2 * t), n, 'saw'), 500) * 0.3
    tyres = bp(g.r.standard_normal(n), 300, 3000) * 0.25
    src = siren + engine + tyres
    y = flyby(src, L, 22.0, 9.0, 6.0, 0.0)
    out = space(y, street_ir(g, 2.0, 3.2), wet=1.0)
    export(D6 + 'パトカーサイレン通過', out, -17)


def elevator():
    g = Gen(605)
    out = np.zeros((ns(4.0), 2))
    n = ns(1.6)
    run = lp(g.brown(1.6), 200) * env_points(n, [(0, 0.6), (1.2, 0.5), (1.6, 0)]) * 0.6
    run += osc(120, n, 'sine') * 0.05 * env_points(n, [(0, 1), (1.6, 0)])
    out = place(out, stereo(run, 0), 0)
    out = place(out, stereo(thunk(g, 90, 0.08, 0.6), 0), 1.55)
    out = place(out, stereo(fm_bell(ns(1.5), 1046.5, 3.5, 1.0, 0.5) * 0.3 +
                            fm_bell(ns(1.5), 1318.5, 3.5, 1.0, 0.5) * 0.22, 0), 1.75)
    dn = ns(1.0)
    door = servo(g, 1.0, 160, 130, 0.15) + lp(g.r.standard_normal(dn), 700) * env_points(dn, [(0, 0), (0.1, 1), (0.9, 1), (1.0, 0)]) * 0.15
    out = place(out, stereo(door, 0), 2.2)
    out = place(out, stereo(thunk(g, 110, 0.05, 0.4), 0), 3.15)
    out = space(out, indoor_ir(g, 0.6), wet=0.5)
    export(D6 + 'エレベーター到着', out, -18)


JOBS = {
    'katana': katana_draw, 'swing': blade_swings, 'bladehit': blade_hit, 'armblade': arm_blade,
    'punch': punches, 'cyberpunch': cyber_punch,
    'jackin': jack_in, 'quickhack': quickhack, 'granted': access_granted, 'denied': access_denied,
    'ice': ice_alert, 'alarm': facility_alarm, 'short': short_circuit, 'glitch': glitch,
    'flatline': flatline, 'scan': scan, 'unlock': door_unlock,
    'door': auto_door, 'drone': drone, 'av': av_flyby, 'siren': siren_pass, 'elevator': elevator,
}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
