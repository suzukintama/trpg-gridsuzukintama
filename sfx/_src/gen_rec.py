"""Version 2: built on real CC0 recordings (sfx/_src/rec/), with the synthesized
street echo / shells / sparks layered where they help.

Sources and licences: rec/guns/CREDITS_smokeem.md, rec/kenney/License_*.txt, rec/amb/CREDITS.md
"""
import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal

from dsp import (SR, Gen, ns, tvec, lp, hp, bp, peak, env_exp, env_ad, env_points, sweep_sine,
                 modal, metal_modes, sat, stereo, place, osc, block_filter, crackle, autopan,
                 make_ir, seamless, fade)
from master import export
from weapons import (gunshot, mech_click, thunk, shell_drop, whoosh, street_ir, indoor_ir, hall_ir,
                     space, electric_arc)
from gen_hits import close_room, debris, metal_hit, explosion_core
from gen_misc import servo, flyby, fm_bell, blade_ring
from gen_amb import car_pass, horn, neon_buzz, rain_bed

REC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rec')
D1, D2, D3, D4, D7 = '01_銃/', '02_被弾・着弾/', '03_爆発/', '04_近接/', '07_環境音ループ/'
_cache = {}


def load(rel, mono=True, pitch=1.0):
    """Load a recording at SR. pitch > 1 plays it faster/higher (tape-style)."""
    key = (rel, mono)
    if key not in _cache:
        path = os.path.join(REC, rel)
        if path.endswith('.wav'):
            y, sr = sf.read(path, always_2d=True)
        else:
            with tempfile.TemporaryDirectory() as td:
                w = os.path.join(td, 'x.wav')
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, w], check=True)
                y, sr = sf.read(w, always_2d=True)
        if sr != SR:
            g = np.gcd(SR, sr)
            y = signal.resample_poly(y, SR // g, sr // g, axis=0)
        _cache[key] = y.mean(1) if mono else (y if y.shape[1] == 2 else np.repeat(y, 2, 1))
    y = _cache[key]
    if pitch != 1.0:
        n = int(len(y) / pitch)
        y = np.stack([np.interp(np.arange(n) * pitch, np.arange(len(y)), y[:, c]) for c in range(y.shape[1])], 1) \
            if y.ndim == 2 else np.interp(np.arange(n) * pitch, np.arange(len(y)), y)
    return y.copy()


def norm(y):
    return y / (np.max(np.abs(y)) + 1e-12)


# ================================================================ 01 guns
def take(g, names, pitch=0.03):
    """Pick a random take with a little pitch/level variation (round-robin feel)."""
    n = names[g.r.integers(len(names))]
    return norm(load(f'guns/{n}.wav', pitch=g.u(1 - pitch, 1 + pitch))) * g.u(0.88, 1.0)


def weight(y, cal=1.0, amt=0.35):
    """A little extra chest thump under the close-mic recording."""
    n = len(y)
    th = sweep_sine(n, 150 / cal ** 0.3, 45, 0.03 * cal) * env_ad(n, 0.001, 0.06 * cal) * amt
    return y + th


def rec_burst(seed, name, takes, rpm, count, ir_kind='street', tail=2.6, cal=1.0, shells=True,
              thump=0.3, jitter=0.005):
    g = Gen(seed)
    dt = 60 / rpm
    times = [0.0] + [i * dt + g.u(-jitter, jitter) for i in range(1, count)]
    out = np.zeros(ns(times[-1] + 1.0))
    for i, t0 in enumerate(times):
        s = weight(take(g, takes), cal, thump) * (1.0 if i == 0 else g.u(0.85, 0.95))
        out = place(out, s, t0)
    ir = {'street': lambda: street_ir(g, 1.0, tail), 'indoor': lambda: indoor_ir(g, 0.85),
          'far': lambda: street_ir(g, 1.8, tail)}[ir_kind]()
    out = space(out, ir, wet=1.0)
    if shells:
        out = place(out, shell_drop(g, 0.0, min(count, 8), pan=0.6, length=times[-1] + 1.5), 0.15, 0.35)
    export(D1 + name, out, drive=3)


def pistol_real():
    g = Gen(1101)
    dry = weight(take(g, ['pistol-1', 'pistol-2', 'pistol-3']), 0.85, 0.25)
    out = space(dry, street_ir(g, 1.0, 2.2), wet=1.0)
    out = place(out, shell_drop(g, 0.0, 1, pan=0.5, length=1.4), 0.32, 0.45)
    export(D1 + '拳銃_単発_実録', out, drive=3)


def shotgun_real():
    g = Gen(1110)
    shot = norm(load('guns/shotgun-1.wav'))
    seq = np.zeros(ns(2.2))
    seq = place(seq, shot, 0)
    seq = place(seq, norm(load('guns/pump.wav')) * 0.15, 0.6)
    out = space(seq, street_ir(g, 1.1, 2.8), wet=1.0)
    out = place(out, stereo(norm(load('guns/shell-2.wav')) * 0.12, 0.5), 1.25)
    export(D1 + 'ショットガン+ポンプ', out, drive=6)


def sniper_real():
    g = Gen(1111)
    shot = weight(norm(load('guns/marksman-2.wav', pitch=0.9)), 1.6, 0.7)
    n = len(shot)
    shot += sweep_sine(n, 90, 28, 0.08) * env_ad(n, 0.003, 0.2) * 0.35  # big-rifle pressure
    seq = np.zeros(ns(4.6))
    seq = place(seq, sat(shot, 1.2), 0)
    # bolt: real rifle-handling clicks from the reload recording, kept quiet
    rl = norm(load('guns/reload.wav'))
    seq = place(seq, rl[ns(0.85):ns(1.25)] * 0.22, 1.35)
    out = space(seq, street_ir(g, 1.8, 4.0), wet=1.0)
    export(D1 + 'スナイパーライフル', out, drive=3)


def reloads_real():
    g = Gen(1113)
    out = space(norm(load('guns/reloadPistol.wav')), indoor_ir(g, 0.4), wet=0.18)
    export(D1 + 'リロード_拳銃', out, -20)
    out = space(norm(load('guns/reload.wav')), indoor_ir(g, 0.45), wet=0.2)
    export(D1 + 'リロード_ライフル', out, -19)


def smart_real():
    """Smart gun: lock-on chirps (synth) + real SMG rounds + guided-round trails."""
    g = Gen(1120)
    seq = np.zeros(ns(2.4))
    for t0, f in [(0.0, 1900), (0.12, 2250), (0.24, 2650)]:
        m = ns(0.06)
        tone = lp(osc(f, m, 'square') * 0.25 + osc(f * 2, m, 'sine') * 0.2, 7000) * env_ad(m, 0.002, 0.02)
        seq = place(seq, tone * 0.22, t0)
    m = ns(0.18)
    seq = place(seq, (osc(3200, m, 'sine') + 0.4 * osc(4800, m, 'sine')) * env_ad(m, 0.003, 0.06) * 0.22, 0.38)
    t0 = 0.62
    for i in range(5):
        seq = place(seq, weight(take(g, ['smg-1', 'smg-2', 'smg-3']), 0.9, 0.25), t0)
        seq = place(seq, whoosh(g, 0.35, 1500, 7000, peak_at=0.15, amp=0.2), t0 + 0.006)
        t0 += 60 / 900 + g.u(-0.004, 0.004)
    out = space(seq, street_ir(g, 1.0, 2.3), wet=1.0)
    for i in range(5):
        trail = whoosh(g, 0.5, 2500, 9000, peak_at=0.2, amp=0.1)
        out = place(out, autopan(trail, np.linspace(0, g.u(-0.9, 0.9), ns(0.5))), 0.66 + i * 0.067)
    export(D1 + 'スマートガン_ロック射撃', out, drive=3)


def distant_real():
    g = Gen(1130)
    L = 9.0
    seq = np.zeros(ns(L + 0.8))
    t0 = 0.2
    while t0 < L - 0.5:
        if g.u() < 0.45:
            for k in range(int(g.u(1, 4))):
                seq = place(seq, take(g, ['pistol-1', 'pistol-2', 'marksman-1']) * g.u(0.3, 0.8), t0)
                t0 += g.u(0.15, 0.5)
        else:
            rpm = g.u(600, 900)
            for k in range(int(g.u(3, 9))):
                seq = place(seq, take(g, ['shot-1', 'shot-2', 'shot-3', 'shot-4']) * g.u(0.3, 0.7), t0)
                t0 += 60 / rpm
        t0 += g.u(0.4, 1.4)
    dry = peak(lp(seq, 1700, 4), 300, 0.8, 3)
    out = lp(space(dry, street_ir(g, 3.0, 4.5), wet=1.0, dry_gain=0.35, width=0), 3200, 2)
    export(D1 + '遠くの銃撃戦', out, -22)


# ================================================================ 02 hits (Kenney CC0 recordings)
def kn(name, pitch=1.0):
    return norm(load(f'kenney/{name}.ogg', pitch=pitch))


def bullet_snap(g, amt=0.5):
    n = ns(0.05)
    return hp(g.r.standard_normal(n), 2500) * env_ad(n, 0.0001, 0.0025) * amt


def flesh_real():
    for i, (seed, punch, soft, p) in enumerate([(1201, 'impactPunch_heavy_000', 'impactSoft_heavy_001', 1.0),
                                                 (1202, 'impactPunch_heavy_003', 'impactSoft_heavy_004', 0.88),
                                                 (1203, 'impactPunch_medium_002', 'impactSoft_medium_000', 1.08)], 1):
        g = Gen(seed)
        y = np.zeros(ns(0.8))
        y = place(y, bullet_snap(g, 0.45), 0)
        y = place(y, kn(punch, p), 0.002)
        y = place(y, kn(soft, p * 0.9) * 0.7, 0.004)
        out = space(y, close_room(g), wet=0.5, width=0.05)
        export(D2 + f'被弾_肉体{i}', out, -15, max_gr=6)


def armor_real():
    g = Gen(1205)
    y = np.zeros(ns(1.0))
    y = place(y, bullet_snap(g, 0.6), 0)
    y = place(y, kn('impactPlate_heavy_002'), 0.001)
    y = place(y, kn('impactPunch_heavy_001', 0.85) * 0.6, 0.004)
    export(D2 + '被弾_防弾プレート', space(y, close_room(g), wet=0.5), -15, max_gr=6)


def cyber_real():
    g = Gen(1206)
    n = ns(1.6)
    t = tvec(n)
    y = np.zeros(n)
    y = place(y, bullet_snap(g, 0.5), 0)
    y = place(y, kn('impactMetal_heavy_001'), 0.001)
    y = place(y, kn('impactPunch_heavy_002', 0.9) * 0.5, 0.004)
    sparks = electric_arc(g, 1.6, 1.0, hum=False) * env_exp(n, 0.22) * 0.35
    f = 1100 * (1 - 0.5 * np.clip((t - 0.05) / 0.9, 0, 1)) + 40 * np.sin(2 * np.pi * 13 * t)
    gate = lp((np.sin(2 * np.pi * 21 * t + 3 * np.sin(2 * np.pi * 3 * t)) > -0.2).astype(float), 300)
    whine = lp(osc(f, n, 'saw'), 4000) * gate * env_ad(n, 0.04, 0.35, delay=0.05) * 0.12
    y = y + sparks + whine
    export(D2 + '被弾_サイバーウェア', space(y, close_room(g), wet=0.5), -14, max_gr=6)


def concrete_real():
    g = Gen(1207)
    out = np.zeros((ns(1.6), 2))
    for t0, nm in [(0.0, 'impactMining_001'), (0.42, 'impactMining_003')]:
        y = np.zeros(ns(1.0))
        y = place(y, bullet_snap(g, 0.7), 0)
        y = place(y, kn(nm, g.u(1.05, 1.2)), 0.001)
        y = place(y, debris(g, 0.9, 1400, 600, 8000, tau=0.0006, decay=0.12) * 0.6, 0.004)
        out = place(out, stereo(y, g.u(-0.5, 0.5)), t0)
    export(D2 + '着弾_コンクリート', space(out, street_ir(g, 0.7, 1.5), wet=0.8), -15, max_gr=6)


def metal_real():
    g = Gen(1208)
    out = np.zeros((ns(2.0), 2))
    for t0, nm in [(0.0, 'impactMetal_medium_000'), (0.33, 'impactMetal_light_002'), (0.52, 'impactMetal_medium_003')]:
        y = np.zeros(ns(1.2))
        y = place(y, bullet_snap(g, 0.6), 0)
        y = place(y, kn(nm), 0.001)
        out = place(out, stereo(y, g.u(-0.6, 0.6)), t0)
    export(D2 + '着弾_金属', space(out, street_ir(g, 0.7, 1.4), wet=0.7), -15, max_gr=6)


def glass_real():
    g = Gen(1209)
    out = np.zeros((ns(2.4), 2))
    out = place(out, stereo(bullet_snap(g, 0.2)), 0)
    out = place(out, stereo(kn('impactGlass_heavy_000')), 0.001)
    out = place(out, stereo(kn('impactGlass_heavy_002', 1.1) * 0.8, 0.3), 0.06)
    for k, nm in enumerate(['impactGlass_medium_001', 'impactGlass_light_000', 'impactGlass_light_003',
                            'impactGlass_medium_004', 'impactGlass_light_002', 'impactGlass_light_004']):
        out = place(out, stereo(kn(nm, g.u(0.95, 1.2)) * g.u(0.25, 0.5) * np.exp(-k / 4), g.u(-0.8, 0.8)),
                    0.35 + k * g.u(0.08, 0.2))
    export(D2 + 'ガラス破砕', space(out, indoor_ir(g, 0.7), wet=0.5), -14, max_gr=6)


# ================================================================ 03 explosions
def grenade_real():
    g = Gen(1301)
    pre = np.zeros(ns(1.6))
    pre = place(pre, kn('metalClick') * 0.35, 0.0)
    pre = place(pre, kn('metalLatch') * 0.3, 0.25)
    for t0, a in [(0.75, 0.55), (0.98, 0.3), (1.12, 0.18)]:
        pre = place(pre, kn('impactMetal_light_001', g.u(0.9, 1.1)) * a, t0)
    boom = norm(load('guns/boom-1.wav')) * 1.0
    core = explosion_core(g, 0.9, 4.0) * 0.45  # longer roar under the real bang
    seq = np.zeros(ns(8))
    seq = place(seq, pre, 0)
    seq = place(seq, boom, 1.6)
    seq = place(seq, core, 1.6)
    seq = place(seq, debris(g, 3.0, 300, 300, 6000, tau=0.002, decay=0.8) * 0.5, 1.75)
    export(D3 + '手榴弾_投擲から爆発', space(seq, street_ir(g, 1.6, 3.5), wet=1.0), drive=4)


def big_real():
    g = Gen(1302)
    seq = np.zeros(ns(11))
    seq = place(seq, norm(load('guns/boom-2.wav')), 0)
    seq = place(seq, norm(load('guns/boom-1.wav', pitch=0.8)) * 0.8, 0.02)
    seq = place(seq, explosion_core(g, 1.6, 7.0) * 0.5, 0)
    t0 = 0.6
    while t0 < 4.5:
        if g.u() < 0.6:
            nm = ['impactMetal_heavy_000', 'impactMetal_heavy_003', 'impactPlate_heavy_001', 'impactGlass_light_001'][g.r.integers(4)]
            seq = place(seq, kn(nm, g.u(0.7, 1.0)) * g.u(0.1, 0.4) * np.exp(-(t0 - 0.6) / 2), t0)
        t0 += g.u(0.05, 0.3)
    fn = ns(9)
    fire = crackle(g, fn, 250, tau=0.0015, lo=300, hi=5000) * 1.2 + lp(g.brown(9), 500) * 0.2
    fire *= env_points(fn, [(0, 0), (1.0, 1), (5, 0.7), (9, 0)])
    seq = place(seq, fire, 1.0)
    export(D3 + '大爆発_車両', space(seq, street_ir(g, 2.0, 4.5), wet=1.0), drive=4)


# ================================================================ 04 melee
def melee_real():
    g = Gen(1401)
    # punches
    out = np.zeros((ns(1.3), 2))
    for k, (t0, pan, nm) in enumerate([(0.0, -0.3, 'impactPunch_medium_001'), (0.42, 0.3, 'impactPunch_heavy_004')]):
        out = place(out, autopan(whoosh(g, 0.15, 400, 1800, 0.8, amp=0.3), np.linspace(-pan, pan, ns(0.15))), t0)
        out = place(out, stereo(kn(nm), pan * 0.5), t0 + 0.13)
    export(D4 + '打撃_パンチ', space(out, close_room(g), wet=0.5), -15, max_gr=6)
    # cyber arm
    out = np.zeros((ns(2.0), 2))
    out = place(out, stereo(servo(g, 0.3, 120, 260, 0.25), 0), 0.0)
    hn = ns(0.25)
    out = place(out, stereo(bp(g.r.standard_normal(hn), 800, 5000) * env_points(hn, [(0, 0), (0.18, 0.6), (0.25, 0)]) * 0.35, 0), 0.05)
    out = place(out, autopan(whoosh(g, 0.2, 200, 1400, 0.85, amp=0.5), np.linspace(-0.4, 0.2, ns(0.2))), 0.12)
    out = place(out, stereo(kn('impactPunch_heavy_000', 0.8), 0.1), 0.3)
    out = place(out, stereo(kn('impactPlate_medium_001', 0.85) * 0.5, 0.1), 0.302)
    hit = sweep_sine(ns(0.5), 110, 35, 0.04) * env_ad(ns(0.5), 0.002, 0.12) * 0.6
    out = place(out, stereo(hit, 0), 0.3)
    rn = ns(0.4)
    out = place(out, stereo(bp(g.r.standard_normal(rn), 2000, 9000) * env_ad(rn, 0.01, 0.1) * 0.25, -0.2), 0.48)
    out = place(out, stereo(kn('metalLatch') * 0.3, -0.2), 0.47)
    export(D4 + '打撃_サイバーアーム', space(out, close_room(g), wet=0.6), -14)
    # blade hit: real slice + swing
    out = np.zeros((ns(2.5), 2))
    out = place(out, autopan(whoosh(g, 0.3, 300, 2200, 0.55, amp=0.6), np.linspace(-0.6, 0.2, ns(0.3))), 0)
    out = place(out, stereo(kn('knifeSlice'), 0.1), 0.2)
    out = place(out, stereo(kn('impactSoft_heavy_002') * 0.7, 0.1), 0.205)
    out = place(out, stereo(blade_ring(g, 4.0, 2600, 0.05), 0.2), 0.21)
    export(D4 + '斬撃_命中', space(out, close_room(g), wet=0.5), -15, max_gr=6)


# ================================================================ 07 ambience on recordings
LR, XR = 54.0, 4.0     # loop length / crossfade for recording-based beds (needs 58 s of source)


def bed(name, start=0.0, gain=1.0, lo=None, hi=None):
    y = load(f'amb/{name}.ogg', mono=False)[ns(start):ns(start + LR + XR)]
    if lo:
        y = hp(y, lo)
    if hi:
        y = lp(y, hi, 4)
    return y * gain


def loop_out(y):
    y = y[:ns(LR + XR)]
    if len(y) < ns(LR + XR):
        y = np.pad(y, ((0, ns(LR + XR) - len(y)), (0, 0)))
    return seamless(y, LR, XR)


def events(g, rate, start=XR + 0.3, end=LR - 3.0):
    t, out = start + g.u(0, 1 / rate), []
    while t < end:
        out.append(t)
        t += g.r.exponential(1 / rate)
    return out


def nightlife_real():
    g = Gen(1702)
    T = LR + XR
    n = ns(T)
    crowd = bed('cafe_murmur', 0, 1.0, lo=120, hi=6000)
    crowd = space(crowd, street_ir(g, 1.2, 1.6), wet=0.8, width=0)[:n]  # take the restaurant outdoors
    out = crowd * 1.0
    out += bed('park_city', 0, 0.45, hi=1300)[:n]  # traffic bed; low-pass removes the birdsong
    out = np.pad(out, ((0, ns(12)), (0, 0)))
    for t0 in events(g, 0.18, end=LR - 8):
        out = place(out, car_pass(g) * g.u(0.08, 0.16), t0)
    for t0 in events(g, 0.1):
        out = place(out, stereo(horn(g) * 0.04, g.u(-0.8, 0.8)), t0)
    for t0 in events(g, 0.04, end=LR - 10):
        m = ns(9)
        src = osc(3200, m, 'sine') * 0.2 + osc(1600, m, 'sine') * 0.15 + lp(g.r.standard_normal(m), 2500) * 0.8
        out = place(out, flyby(src, 9, 40, 60, 4.5, 40) * 0.25, t0)
    out[:n] += stereo(neon_buzz(g, T, 0.1), 0.7)[:n] * 0.06
    export(D7 + '夜の繁華街', loop_out(out), -20, loop=True, ogg=True)


def car_real():
    g = Gen(1708)
    T = LR + XR
    n = ns(T)
    out = bed('bus_ride', 1.5, 0.8, hi=2500)  # engine + road from inside a vehicle
    out = out + bed('rain_heavy', 0, 0.7, hi=2200)  # rain drumming on the roof
    out = np.pad(out, ((0, ns(3)), (0, 0)))
    out[:n] += np.stack([crackle(g, n, 250, tau=0.0006, lo=800, hi=6000) for _ in range(2)], 1) * 0.12
    per = 1.5  # wipers: 36 sweeps per 54 s loop
    for k in range(int(T / per) + 1):
        t0 = k * per
        m = ns(0.55)
        tt = tvec(m)
        sw = bp(g.r.standard_normal(m), 600, 4500) * np.sin(np.pi * tt / 0.55) ** 2 * 0.2
        mot = lp(osc(95, m, 'saw'), 600) * 0.06 * np.sin(np.pi * tt / 0.55)
        pan = np.linspace(-0.6, 0.6, m) if k % 2 == 0 else np.linspace(0.6, -0.6, m)
        out = place(out, autopan(sw + mot, pan), t0)
        th = ns(0.15)
        out = place(out, stereo(sweep_sine(th, 160, 90, 0.01) * env_ad(th, 0.001, 0.02) * 0.12, pan[-1]), t0 + 0.55)
    export(D7 + '車内_雨の夜', loop_out(out), -21, loop=True, ogg=True)


def server_real():
    g = Gen(1705)
    T = LR + XR
    n = ns(T)
    out = bed('ac_room', 0, 1.0)
    out = np.pad(out, ((0, ns(2)), (0, 0)))
    for f in [212.0, 213.7, 318.4]:
        out[:n] += stereo(osc(f, n, 'sine') * 0.012, g.u(-0.8, 0.8))
    out[:n] += stereo(osc(13800, n, 'sine') * 0.002, 0.4)
    for t0 in events(g, 1.2, start=0.3, end=T - 0.3):
        for k in range(int(g.u(1, 6))):
            m = ns(0.01)
            c = hp(g.r.standard_normal(m), 2500) * env_ad(m, 0.0001, 0.0008)
            out = place(out, stereo(c * 0.05, g.u(-0.8, 0.8)), t0 + k * g.u(0.01, 0.04))
    for t0 in events(g, 0.05, end=LR - 1):
        m = ns(0.12)
        out = place(out, stereo(osc(2093, m, 'sine') * env_ad(m, 0.002, 0.04) * 0.03, g.u(-0.6, 0.6)), t0)
    export(D7 + 'サーバールーム', loop_out(out), -22, loop=True, ogg=True)


def alley_real():
    g = Gen(1703)
    T = LR + XR
    n = ns(T)
    out = bed('park_city', 0, 0.5, hi=700)  # distant city, birds filtered out
    out = out + bed('ac_room', 0, 0.35, lo=80, hi=3000)  # rooftop HVAC units
    out = np.pad(out, ((0, ns(6)), (0, 0)))
    out[:n] += stereo(neon_buzz(g, T, 0.5), -0.55)[:n] * 0.18
    for t0 in events(g, 0.06, end=LR - 6):
        m = ns(g.u(2.5, 5))
        y = bp(g.r.standard_normal(m), 900, 8000) * env_points(m, [(0, 0), (0.3, 1), (m / SR * 0.7, 0.8), (m / SR, 0)])
        out = place(out, stereo(y * 0.04, 0.5), t0)
    for t0 in events(g, 0.06):
        nm = ['impactMetal_light_000', 'impactTin_medium_002', 'impactPlank_medium_001'][g.r.integers(3)]
        out = place(out, stereo(lp(kn(nm, g.u(0.8, 1.0)), 3000) * 0.05, g.u(-0.8, 0.8)), t0)
    s = lp(norm(load('guns/shot-2.wav')), 1500) * 0.08
    out = place(out, stereo(s, -0.5), 36.0)
    out = space(out, street_ir(g, 0.8, 1.6), wet=0.6, width=0)
    export(D7 + '裏路地', loop_out(out), -22, loop=True, ogg=True)


def factory_real():
    g = Gen(1707)
    T = LR + XR
    n = ns(T)
    out = bed('ac_room', 0, 0.5, hi=900)  # big extraction fans far away
    out = np.pad(out, ((0, ns(6)), (0, 0)))
    cyc = 4.5  # press cycle, 12 per 54 s loop
    for k in range(int(T / cyc) + 1):
        t0 = k * cyc
        m = ns(1.2)
        whirr = lp(osc(70 * (1 + 0.5 * tvec(m)), m, 'saw'), 600) * env_points(m, [(0, 0), (0.6, 1), (1.2, 0)]) * 0.08
        out = place(out, stereo(whirr, 0.6), t0)
        slam = kn(['impactMetal_heavy_002', 'impactPlate_heavy_000', 'impactMetal_heavy_004'][k % 3], 0.6) * 0.5
        out = place(out, stereo(lp(slam, 3000), 0.6), t0 + 1.25)
        h = ns(1.0)
        out = place(out, stereo(bp(g.r.standard_normal(h), 1200, 7000) * env_ad(h, 0.02, 0.25) * 0.04, 0.6), t0 + 1.4)
    for t0 in events(g, 0.1):
        nm = ['impactBell_heavy_001', 'impactMetal_light_003', 'impactTin_medium_000'][g.r.integers(3)]
        out = place(out, stereo(lp(kn(nm, g.u(0.6, 0.8)), 2500) * 0.08, g.u(-0.9, 0.9)), t0)
    out = space(out, hall_ir(g, 3.5), wet=1.0, width=0)
    export(D7 + '廃工場', loop_out(out), -22, loop=True, ogg=True)


def thunderstorm_real():
    out = bed('thunder_storm', 0, 1.0)
    export(D7 + '雷雨', loop_out(out), -20, loop=True, ogg=True)


def metro_real():
    out = bed('metro_cabin', 0, 1.0)
    export(D7 + '地下鉄_車内', loop_out(out), -21, loop=True, ogg=True)


JOBS = {
    'smg': lambda: rec_burst(1106, 'SMG_連射', ['smg-1', 'smg-2', 'smg-3'], 900, 7, cal=0.8),
    'smg_in': lambda: rec_burst(1109, 'SMG_屋内連射', ['smg-1', 'smg-2', 'smg-3'], 900, 9, 'indoor', cal=0.8),
    'ar3': lambda: rec_burst(1107, 'アサルトライフル_3点', ['shot-1', 'shot-2', 'shot-3', 'shot-4'], 700, 3, tail=2.6),
    'arfull': lambda: rec_burst(1108, 'アサルトライフル_フルオート', ['shot-1', 'shot-2', 'shot-3', 'shot-4'], 650, 14, tail=2.8),
    'pistol_real': pistol_real, 'shotgun': shotgun_real, 'sniper': sniper_real, 'reload': reloads_real,
    'smart': smart_real, 'distant': distant_real,
    'flesh': flesh_real, 'armor': armor_real, 'cyber': cyber_real, 'concrete': concrete_real,
    'metal': metal_real, 'grenade': grenade_real, 'big': big_real, 'melee': melee_real,
    'night': nightlife_real, 'car': car_real, 'server': server_real, 'alley': alley_real,
    'factory': factory_real, 'storm': thunderstorm_real, 'metro': metro_real,
}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
