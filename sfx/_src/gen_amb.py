"""07_環境音ループ : seamless 60 s ambience beds (register these as BGM in the VTT)."""
import numpy as np

from dsp import (SR, Gen, ns, tvec, lp, hp, bp, peak, env_exp, env_ad, env_points, sweep_sine,
                 modal, metal_modes, sat, stereo, place, osc, block_filter, crackle, autopan,
                 bitcrush, make_ir, seamless, fade, shelf_low)
from master import export
from weapons import street_ir, indoor_ir, hall_ir, space, gunshot
from gen_misc import flyby, fm_bell

D7 = '07_環境音ループ/'
L = 60.0   # loop length
X = 4.0    # crossfade used to close the loop
T = L + X  # rendered length before folding


def ev_times(g, rate, tail=3.0, start=None, end=None):
    """Poisson event times kept away from the loop seam."""
    start = X + 0.3 if start is None else start
    end = L - tail if end is None else end
    out = []
    t = start + g.u(0, 1 / rate)
    while t < end:
        out.append(t)
        t += g.r.exponential(1 / rate)
    return out


def slow_lfo(g, n, rate=0.1, depth=0.3):
    """Smooth random modulation around 1.0."""
    k = max(4, int(n / SR * rate * 4))
    pts = g.r.standard_normal(k)
    y = np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)
    y = lp(y, rate * 2, 1) if rate * 2 > 5 else y
    return 1 + depth * y / (np.std(y) + 1e-9)


def to_loop(y, coherent=False):
    if y.ndim == 1:
        y = stereo(y)
    if len(y) < ns(T):
        y = np.pad(y, ((0, ns(T) - len(y)), (0, 0)))
    return seamless(y[:ns(T)], L, X, coherent)


# ------------------------------------------------------------ beds & layers
def rain_bed(g, intensity=1.0, dur=T):
    n = ns(dur)
    gust = slow_lfo(g, n, 0.08, 0.18)
    hiss = hp(g.pink(dur), 500) * 0.35
    hiss = lp(hiss, 9000)
    drops = np.stack([crackle(g, n, 2600 * intensity * gust, tau=0.00035, lo=1200, hi=13000) for _ in range(2)], 1)
    patter = np.stack([crackle(g, n, 700 * intensity, tau=0.0012, lo=300, hi=3500) for _ in range(2)], 1)
    body = np.stack([hiss * gust, hp(g.pink(dur), 500) * 0.35 * gust], 1)
    body = lp(body, 9000)
    return lp(body * 0.6 * intensity + drops * 1.1 + patter * 1.1, 8000)


def plinks(g, rate, f_lo=900, f_hi=3500, gain=0.2, dur=T):
    """Heavier drops hitting metal / puddles."""
    out = np.zeros((ns(dur), 2))
    for t0 in ev_times(g, rate, 0.4, start=0.0, end=dur - 0.4):
        m = ns(0.25)
        f = g.u(f_lo, f_hi)
        tt = tvec(m)
        y = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.6 * np.exp(-tt / 0.01))) / SR) * env_ad(m, 0.0005, g.u(0.01, 0.05))
        out = place(out, stereo(y * g.u(0.3, 1) * gain, g.u(-0.9, 0.9)), t0)
    return out


def city_drone(g, dur=T, level=1.0):
    n = ns(dur)
    rum = lp(g.brown(dur), 180) * 0.8 * slow_lfo(g, n, 0.05, 0.2)
    far = lp(hp(g.pink(dur), 120), 900) * 0.35 * slow_lfo(g, n, 0.07, 0.25)
    far2 = lp(hp(g.pink(dur), 120), 900) * 0.35 * slow_lfo(g, n, 0.07, 0.25)
    return np.stack([rum + far, rum + far2], 1) * level


def car_pass(g, wet_road=False):
    dur = g.u(6, 9)
    n = ns(dur)
    t = tvec(n)
    rpm = g.u(28, 45)
    eng = lp(osc(rpm * (1 + 0.03 * np.sin(2 * np.pi * 0.3 * t)), n, 'saw'), 400) * 0.4
    eng += lp(g.brown(dur), 250) * 0.5
    tyre = bp(g.r.standard_normal(n), 400, 3000) * 0.35
    if wet_road:
        tyre += hp(g.r.standard_normal(n), 1500) * 0.6  # spray hiss
    # electric cars: add a faint inverter whine
    if g.u() < 0.5:
        eng += osc(g.u(700, 1400), n, 'sine') * 0.03
    src = eng + tyre
    return flyby(src, dur, g.u(9, 16), g.u(5, 14), dur / 2, 0.0, 1 if g.u() > 0.5 else -1)


def horn(g):
    m = ns(g.u(0.25, 0.7))
    f = g.u(380, 470)
    y = (osc(f, m, 'saw') + osc(f * 1.26, m, 'saw')) * 0.3
    y = lp(y, 2500) * env_points(m, [(0, 0), (0.01, 1), (m / SR - 0.03, 1), (m / SR, 0)])
    return y


def neon_buzz(g, dur=T, flicker=0.2):
    n = ns(dur)
    t = tvec(n)
    # 100/120 Hz magnetostriction buzz rich in harmonics + transformer hum
    b = np.sign(np.sin(2 * np.pi * 120 * t)) * 0.4 + osc(60, n, 'sine') * 0.2
    b = bp(b, 100, 5000)
    b = peak(b, 2400, 3, 6)
    level = np.ones(n)
    # flickers: brief dropouts with crackle
    cr = np.zeros(n)
    for t0 in ev_times(g, flicker, 1.0, start=0.0, end=dur - 1.0):
        i = ns(t0)
        k = ns(g.u(0.05, 0.4))
        pat = (g.r.random(k // 240 + 1) > 0.5).astype(float)
        pat = np.repeat(pat, 240)[:k]
        level[i:i + k] = 0.15 + 0.85 * pat
        cr[i:i + k] += crackle(g, k, 1500, tau=0.0003, lo=2000, hi=12000) * 0.8
    level = lp(level, 200, 1)
    return b * level * 0.25 + cr


def distant_siren(g, dur=11.0):
    n = ns(dur)
    t = tvec(n)
    ph = (t % 3.4) / 3.4
    f = 600 + 650 * np.sin(np.pi * ph) ** 1.5
    y = osc(f, n, 'square') * 0.4
    y = lp(bp(y, 400, 3000), 1600)
    y *= env_points(n, [(0, 0), (dur * 0.4, 1), (dur * 0.6, 1), (dur, 0)])
    return y


def thunder(g, dur=9.0):
    n = ns(dur)
    y = lp(g.brown(dur), 260) * env_points(n, [(0, 0), (0.25, 0.6), (0.5, 1.0), (1.4, 0.7), (dur, 0)]) ** 1.5
    rumbles = crackle(g, n, 40 * env_exp(n, 1.5), tau=0.02, lo=40, hi=400) * 2
    return y + rumbles


def voice(g, dur):
    """One babbling voice (no real words): glottal buzz through moving formants."""
    n = ns(dur)
    female = g.u() < 0.5
    f0b = g.u(165, 240) if female else g.u(90, 140)
    vowels = [(730, 1090, 2440), (270, 2290, 3010), (530, 1840, 2480), (570, 840, 2410),
              (300, 870, 2240), (660, 1720, 2410), (440, 1020, 2240)]
    scale = 1.15 if female else 1.0
    # talk spurts / pauses
    amp_pts, f_pts, f0_pts = [], [], []
    t = 0.0
    while t < dur:
        spurt = g.u(0.8, 3.5)
        t_end = min(dur, t + spurt)
        pitch = f0b * g.u(0.95, 1.1)
        while t < t_end:
            syl = g.u(0.12, 0.26)
            v = vowels[g.r.integers(len(vowels))]
            amp_pts += [(t, 0.05), (t + syl * 0.3, g.u(0.6, 1)), (t + syl * 0.8, 0.15)]
            f_pts.append((t + syl * 0.4, v))
            f0_pts.append((t + syl * 0.4, pitch))
            pitch *= g.u(0.96, 1.02)
            t += syl
        amp_pts.append((t + 0.01, 0.0))
        t += g.u(0.3, 1.6)
    at, av = zip(*amp_pts)
    amp = np.interp(tvec(n), at, av)
    ft = [p[0] for p in f_pts]
    F = [np.interp(tvec(n), ft, [p[1][i] * scale for p in f_pts]) for i in range(3)]
    f0 = np.interp(tvec(n), [p[0] for p in f0_pts], [p[1] for p in f0_pts])
    f0 *= 1 + 0.01 * g.r.standard_normal(n).cumsum() / np.sqrt(n)  # jitter
    ph = np.cumsum(f0) / SR
    src = (2 * (ph % 1) - 1) + g.r.standard_normal(n) * 0.15
    src = lp(src, 4500)
    y = (block_filter(src, F[0], 'bandpass', 2, 256, 90) * 1.0 +
         block_filter(src, F[1], 'bandpass', 2, 256, 120) * 0.6 +
         block_filter(src, F[2], 'bandpass', 2, 256, 170) * 0.3)
    return y * lp(amp, 30)


def crowd(g, voices=16, dur=T):
    out = np.zeros((ns(dur), 2))
    for k in range(voices):
        v = voice(g, dur)
        out += stereo(v * g.u(0.4, 1.0), g.u(-0.9, 0.9))
    # occasional laugh-like bursts are just louder spurts; keep it anonymous
    out = lp(out, 3200)
    return out


# ------------------------------------------------------------ loops
def rain_neon_street():
    g = Gen(701)
    n = ns(T)
    out = np.zeros((n + ns(6), 2))
    out[:n] += rain_bed(g, 1.0) * 0.55
    out[:n] += plinks(g, 6, gain=0.5)
    out[:n] += city_drone(g) * 0.35
    out[:n] += stereo(neon_buzz(g, T, 0.15), 0.65) * 0.25
    cars = np.zeros((n + ns(10), 2))
    for t0 in ev_times(g, 0.16, 9):
        cars = place(cars, car_pass(g, wet_road=True) * g.u(0.3, 0.55), t0)
    out += cars[:len(out)]
    # signature events at fixed spots so every loop has them
    out = place(out, stereo(distant_siren(g) * 0.16, -0.5), 9.0)
    out = place(out, stereo(thunder(g), 0.2) * 0.7, 31.0)
    out = place(out, stereo(distant_siren(g) * 0.12, 0.6), 44.0)
    for t0 in ev_times(g, 0.05, 3):
        out = place(out, stereo(horn(g) * 0.08, g.u(-0.8, 0.8)), t0)
    out = space(out, street_ir(g, 1.5, 2.2), wet=0.5, width=0)
    export(D7 + '雨のネオン街', to_loop(out), -20, loop=True, ogg=True)


def nightlife_street():
    g = Gen(702)
    n = ns(T)
    out = np.zeros((n + ns(6), 2))
    out[:n] += crowd(g, 18) * 1.6
    out[:n] += city_drone(g) * 0.4
    cars = np.zeros((n + ns(10), 2))
    for t0 in ev_times(g, 0.2, 9):
        cars = place(cars, car_pass(g) * g.u(0.25, 0.5), t0)
    out += cars[:len(out)]
    for t0 in ev_times(g, 0.12, 2):
        out = place(out, stereo(horn(g) * 0.1, g.u(-0.8, 0.8)), t0)
    # AV flying overhead now and then
    for t0 in ev_times(g, 0.04, 10):
        m = ns(9)
        tt = tvec(m)
        src = (osc(3200, m, 'sine') * 0.2 + osc(1600, m, 'sine') * 0.15 + lp(g.r.standard_normal(m), 2500) * 0.8)
        out = place(out, flyby(src, 9, 40, 60, 4.5, 40) * 0.6, t0)
    # muffled music leaking from a bar door down the street
    m = ns(T)
    tt = tvec(m)
    beat = 60 / 118
    kick = np.zeros(m)
    for k in range(int(T / beat)):
        kk = ns(0.3)
        kick = place(kick, sweep_sine(kk, 120, 45, 0.02) * env_ad(kk, 0.001, 0.08), k * beat)
    music = lp(kick, 160) * 0.12 * slow_lfo(g, m, 0.05, 0.3)
    out[:n] += stereo(music, -0.5)
    out = space(out, street_ir(g, 1.3, 1.8), wet=0.6, width=0)
    export(D7 + '夜の繁華街', to_loop(out), -20, loop=True, ogg=True)


def back_alley():
    g = Gen(703)
    n = ns(T)
    out = np.zeros((n + ns(6), 2))
    out[:n] += city_drone(g, level=0.5)
    # wind through the alley: slow whistling band
    wind = block_filter(g.pink(T), 500 + 350 * slow_lfo(g, n, 0.05, 0.6), 'bandpass', 2, 512, 300)
    out[:n] += stereo(wind * 0.18 * slow_lfo(g, n, 0.06, 0.4), -0.2)
    out[:n] += stereo(neon_buzz(g, T, 0.5), -0.55) * 0.35
    # drips into puddles
    for t0 in ev_times(g, 1.4, 0.5):
        m = ns(0.3)
        f = g.u(1100, 2600)
        tt = tvec(m)
        y = np.sin(2 * np.pi * np.cumsum(f * (1 + 1.2 * np.exp(-tt / 0.006))) / SR) * env_ad(m, 0.0005, 0.03)
        out = place(out, stereo(y * g.u(0.03, 0.09), g.u(-0.7, 0.7)), t0)
    # steam vent bursts
    for t0 in ev_times(g, 0.06, 6):
        m = ns(g.u(2.5, 5))
        y = bp(g.r.standard_normal(m), 900, 8000) * env_points(m, [(0, 0), (0.3, 1), (m / SR * 0.7, 0.8), (m / SR, 0)])
        out = place(out, stereo(y * 0.07, 0.5), t0)
    # far-off metal clanks / a can kicked over
    for t0 in ev_times(g, 0.05, 3):
        m = ns(1.5)
        y = modal(m, metal_modes(g, g.u(400, 900), 10, 0.2, bright=0.8))
        out = place(out, stereo(lp(y, 3000) * 0.05, g.u(-0.8, 0.8)), t0)
    # one distant gunshot in the city (keeps the tension)
    s = lp(gunshot(g, cal=1.0, bright=0.6), 1500) * 0.12
    out = place(out, stereo(s, -0.5), 38.0)
    out = space(out, street_ir(g, 0.8, 1.6), wet=0.8, width=0)
    export(D7 + '裏路地', to_loop(out), -22, loop=True, ogg=True)


def club_through_wall():
    """A club on the other side of the wall. 128 BPM, exactly 32 bars = 60 s."""
    g = Gen(704)
    bpm = 128
    beat = 60 / bpm
    n = ns(T)
    music = np.zeros(n + ns(2))
    # progression (A minor): Am F C G, 4 bars each, repeating
    roots = [55.0, 43.65, 65.41, 49.0]
    for b in range(int(T / beat) + 1):
        t0 = b * beat
        k = ns(0.35)
        kick = sweep_sine(k, 150, 46, 0.018) * env_ad(k, 0.001, 0.11)
        kick += hp(g.r.standard_normal(k), 2000) * env_ad(k, 0.0002, 0.003) * 0.3
        music = place(music, kick * 1.0, t0)
        bar = int(b // 4)
        root = roots[(bar // 4) % 4]
        # rolling offbeat bass (8ths, skipping the kick)
        for half in (0.5,):
            m = ns(beat * 0.45)
            bs = osc(root, m, 'saw') * env_ad(m, 0.003, 0.09)
            music = place(music, lp(bs, 300) * 0.7, t0 + beat * half)
        if b % 2 == 1:  # clap on 2 and 4
            m = ns(0.2)
            cl = bp(g.r.standard_normal(m), 900, 3000) * env_ad(m, 0.001, 0.04)
            music = place(music, cl * 0.5, t0)
        m = ns(0.05)
        hat = hp(g.r.standard_normal(m), 7000) * env_ad(m, 0.0005, 0.01)
        music = place(music, hat * 0.25, t0 + beat * 0.5)
    # sustained pad chords
    pad = np.zeros(n + ns(2))
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
    bar_len = beat * 4
    for c in range(int(T / (bar_len * 4)) + 1):
        ch = chords[c % 4]
        m = ns(bar_len * 4)
        y = sum(osc(f, m, 'saw') + osc(f * 1.006, m, 'saw') for f in ch) * 0.08
        y *= env_points(m, [(0, 0), (0.2, 1), (bar_len * 4 - 0.2, 1), (bar_len * 4, 0)])
        pad = place(pad, y, c * bar_len * 4)
    music = music + lp(pad, 1200) * 0.5
    music = music[:n]
    # the wall: heavy low-pass + body resonance; a whisper of highs leaks through
    wall = lp(music, 220, 4) * 1.6 + bp(music, 2000, 5000) * 0.015
    wall = peak(wall, 70, 1.2, 5)
    out = stereo(wall, 0) * 0.9
    # muffled crowd behind the wall and the room we're in
    out += stereo(lp(crowd(g, 10).mean(axis=1), 500) * 0.25, 0)
    out += stereo(neon_buzz(g, T, 0.05), 0.7) * 0.12
    hvac = lp(g.brown(T), 300) * 0.1
    out += stereo(hvac, 0)
    out = space(out, indoor_ir(g, 0.6), wet=0.5, width=0)
    # music is periodic in 60 s, so the crossfade is phase-coherent
    export(D7 + 'クラブ_壁越し', to_loop(out, coherent=True), -19, loop=True, ogg=True)


def server_room():
    g = Gen(705)
    n = ns(T)
    t = tvec(n)
    out = np.zeros((n + ns(4), 2))
    # fans: broadband air + blade tones with slow beating between units
    air = np.stack([lp(hp(g.pink(T), 150), 6000), lp(hp(g.pink(T), 150), 6000)], 1) * 0.35
    out[:n] += air
    for f in [212.0, 213.7, 318.4, 425.1]:
        tone = osc(f, n, 'sine') * 0.03
        out[:n] += stereo(tone, g.u(-0.8, 0.8))
    out[:n] += stereo(lp(g.brown(T), 120) * 0.4, 0)  # HVAC
    out[:n] += stereo(osc(100, n, 'sine') * 0.02 + osc(150, n, 'sine') * 0.01, 0)  # mains hum
    whine = osc(13800 + 40 * np.sin(2 * np.pi * 0.2 * t), n, 'sine') * 0.004  # coil whine
    out[:n] += stereo(whine, 0.4)
    # disk seeks / relay clicks
    for t0 in ev_times(g, 1.2, 0.3):
        burst = int(g.u(1, 6))
        for k in range(burst):
            m = ns(0.01)
            c = hp(g.r.standard_normal(m), 2500) * env_ad(m, 0.0001, 0.0008)
            out = place(out, stereo(c * 0.08, g.u(-0.8, 0.8)), t0 + k * g.u(0.01, 0.04))
    # status beeps
    for t0 in ev_times(g, 0.05, 1):
        m = ns(0.12)
        b = osc(2093, m, 'sine') * env_ad(m, 0.002, 0.04) * 0.05
        out = place(out, stereo(b, g.u(-0.6, 0.6)), t0)
    out = space(out, indoor_ir(g, 0.7), wet=0.4, width=0)
    export(D7 + 'サーバールーム', to_loop(out), -22, loop=True, ogg=True)


def netspace():
    """Cyberspace: slow evolving pads, data sparkles, deep sub. 4 chords x 15 s."""
    g = Gen(706)
    n = ns(T)
    t = tvec(n)
    out = np.zeros((n + ns(1), 2))
    chords = [[110.0, 164.81, 220.0, 261.63, 329.63],   # Am9-ish
              [87.31, 130.81, 174.61, 220.0, 329.63],   # Fmaj7
              [98.0, 146.83, 196.0, 246.94, 293.66],    # G
              [82.41, 123.47, 164.81, 207.65, 329.63]]  # E
    seg = 15.0
    for c in range(int(T / seg) + 1):
        ch = chords[c % 4]
        m = ns(seg + 4)
        tt = tvec(m)
        y = np.zeros((m, 2))
        for f in ch:
            for det, pan in [(0.997, -0.7), (1.003, 0.7)]:
                v = osc(f * det, m, 'saw') * 0.05
                y += stereo(v, pan)
        cut = 600 + 900 * (0.5 + 0.5 * np.sin(2 * np.pi * tt / (seg + 4) - np.pi / 2))
        for k in range(2):
            y[:, k] = block_filter(y[:, k], cut, 'lowpass', 2, 512)
        y *= env_points(m, [(0, 0), (4, 1), (seg, 1), (seg + 4, 0)])[:, None]
        out = place(out, y, c * seg - 2 if c else 0)
    sub = osc(55 * (1 + 0.002 * np.sin(2 * np.pi * 0.1 * t)), n, 'sine') * 0.12
    out[:n] += stereo(sub, 0)
    # sparkles: pentatonic sine grains high up
    scale = [880, 987.77, 1174.66, 1318.51, 1567.98, 1760, 1975.53, 2349.32, 2637.02]
    for t0 in ev_times(g, 1.6, 2.5, start=0.0, end=T - 2.5):
        f = scale[g.r.integers(len(scale))]
        m = ns(g.u(0.6, 2.0))
        y = fm_bell(m, f, 2.0, 0.6, m / SR * 0.35, att=0.01) * g.u(0.02, 0.06)
        out = place(out, stereo(y, g.u(-1, 1)), t0)
    # data whispers: sweeping filtered noise
    wh = block_filter(g.r.standard_normal(n), 2000 + 1500 * np.sin(2 * np.pi * t / 7.5), 'bandpass', 2, 512, 600)
    out[:n] += autopan(wh * 0.02, np.sin(2 * np.pi * t / 12))
    ir = make_ir(g, rt60=4.5, predelay=0.03, lp_start=9000, lp_end=3000, tail_energy=1.6)
    out = space(out, ir, wet=1.0, width=0)
    export(D7 + '電脳空間', to_loop(out), -20, loop=True, ogg=True)


def factory():
    g = Gen(707)
    n = ns(T)
    t = tvec(n)
    out = np.zeros((n + ns(6), 2))
    out[:n] += city_drone(g, level=0.3)
    # a still-running press somewhere: slow cycle (whirr - slam - hiss) every 4 s
    cyc = 4.0
    for k in range(int(T / cyc) + 1):
        t0 = k * cyc
        m = ns(1.2)
        whirr = lp(osc(70 * (1 + 0.5 * tvec(m)), m, 'saw'), 600) * env_points(m, [(0, 0), (0.6, 1), (1.2, 0)]) * 0.15
        out = place(out, stereo(whirr, 0.6), t0)
        s = ns(2.0)
        slam = sweep_sine(s, 110, 40, 0.04) * env_ad(s, 0.002, 0.15) * 0.5
        slam += modal(s, metal_modes(Gen(int(7000 + k % 3)), 180, 10, 0.4, bright=0.8)) * 0.1
        out = place(out, stereo(lp(slam, 2500), 0.6), t0 + 1.25)
        h = ns(1.0)
        hiss = bp(g.r.standard_normal(h), 1200, 7000) * env_ad(h, 0.02, 0.25) * 0.08
        out = place(out, stereo(hiss, 0.6), t0 + 1.4)
    # wind through broken windows
    w = block_filter(g.pink(T), 700 + 400 * slow_lfo(g, n, 0.04, 0.5), 'bandpass', 2, 512, 200)
    out[:n] += stereo(w * 0.1 * slow_lfo(g, n, 0.05, 0.5), -0.5)
    # creaking metal (slow pitch glides)
    for t0 in ev_times(g, 0.08, 4):
        m = ns(g.u(1.0, 2.5))
        f = g.u(250, 600) * (1 + 0.3 * np.sin(np.pi * tvec(m) / (m / SR)))
        y = osc(f, m, 'saw') * env_points(m, [(0, 0), (0.2, 1), (m / SR, 0)])
        y = bp(y, 300, 3000) * (0.5 + 0.5 * (g.r.random(m) < 0.3))
        out = place(out, stereo(lp(y, 2500) * 0.03, g.u(-0.8, 0.8)), t0)
    for t0 in ev_times(g, 0.6, 0.5):
        m = ns(0.3)
        f = g.u(900, 2000)
        y = np.sin(2 * np.pi * f * tvec(m)) * env_ad(m, 0.0005, 0.04)
        out = place(out, stereo(y * 0.04, g.u(-0.8, 0.8)), t0)
    # press cycle is 4 s and 60/4 = 15, so the loop stays in time
    out = space(out, hall_ir(g, 3.5), wet=1.0, width=0)
    export(D7 + '廃工場', to_loop(out), -22, loop=True, ogg=True)


def car_rain():
    """Inside a car at night in the rain: engine, road, roof rain, wipers (1.5 s period)."""
    g = Gen(708)
    n = ns(T)
    t = tvec(n)
    out = np.zeros((n + ns(2), 2))
    eng = lp(osc(31 + 0.6 * np.sin(2 * np.pi * 0.07 * t), n, 'saw'), 250) * 0.25
    road = lp(g.brown(T), 220) * 0.6 * slow_lfo(g, n, 0.1, 0.15)
    out[:n] += stereo(eng + road, 0)
    # rain on the roof: muffled dense patter
    roof = rain_bed(g, 0.9)
    out[:n] += lp(roof, 2500) * 0.4
    # windscreen: brighter drops in front
    out[:n] += np.stack([crackle(g, n, 300, tau=0.0006, lo=800, hi=6000) for _ in range(2)], 1) * 0.35
    # wipers
    per = 1.5
    for k in range(int(T / per) + 1):
        t0 = k * per
        m = ns(0.55)
        tt = tvec(m)
        sw = bp(g.r.standard_normal(m), 600, 4500) * np.sin(np.pi * tt / 0.55) ** 2 * 0.45
        squeak = lp(osc(1300 + 200 * np.sin(np.pi * tt / 0.55), m, 'saw'), 4000) * np.sin(np.pi * tt / 0.55) ** 6 * 0.012
        mot = lp(osc(95, m, 'saw'), 600) * 0.12 * np.sin(np.pi * tt / 0.55)
        pan = np.linspace(-0.6, 0.6, m) if k % 2 == 0 else np.linspace(0.6, -0.6, m)
        out = place(out, autopan(sw + squeak + mot, pan), t0)
        th = ns(0.15)
        thk = sweep_sine(th, 160, 90, 0.01) * env_ad(th, 0.001, 0.02) * 0.3
        out = place(out, stereo(thk, pan[-1]), t0 + 0.55)
    # a car passing the other way
    for t0 in ev_times(g, 0.08, 8):
        out = place(out, lp(car_pass(g, wet_road=True), 1800) * g.u(0.2, 0.35), t0)
    out = space(out, make_ir(g, rt60=0.15, predelay=0.001, tail_energy=0.2), wet=1.0, width=0)
    export(D7 + '車内_雨の夜', to_loop(out), -21, loop=True, ogg=True)


JOBS = {
    'rain': rain_neon_street, 'night': nightlife_street, 'alley': back_alley, 'club': club_through_wall,
    'server': server_room, 'net': netspace, 'factory': factory, 'car': car_rain,
}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
