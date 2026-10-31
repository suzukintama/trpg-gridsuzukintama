"""01_銃 : firearms + gun handling."""
import numpy as np

from dsp import (SR, Gen, ns, tvec, lp, hp, bp, peak, env_exp, env_ad, env_points, sweep_sine,
                 modal, metal_modes, sat, compress, stereo, place, osc, block_filter, crackle,
                 autopan, mix, bitcrush, doppler)
from master import export
from weapons import (gunshot, mech_click, thunk, shell_drop, whoosh, street_ir, indoor_ir,
                     hall_ir, space, electric_arc)

D = '01_銃/'


def pistol_one(g, cal=0.85, bright=1.05):
    s = gunshot(g, cal=g.jit(cal, 0.04), bright=g.jit(bright, 0.05), boom=0.9, length=0.5)
    # slide cycling right after the shot
    return place(s, mech_click(g, 3400, 0.10, 0.01), 0.012)


def pistol_single():
    g = Gen(101)
    dry = pistol_one(g)
    out = space(dry, street_ir(g, 1.0, 2.2), wet=1.0)
    out = place(out, shell_drop(g, 0.0, 1, pan=0.5, length=1.4), 0.32, 0.55)
    export(D + '拳銃_単発', out, drive=3)


def pistol_triple():
    g = Gen(102)
    times = [0.0, 0.19, 0.33]
    out = np.zeros(ns(0.9))
    for t0 in times:
        s = pistol_one(g)
        i = ns(t0)
        out[i:i + len(s)] += s[:len(out) - i]
    out = space(out, street_ir(g, 1.0, 2.2), wet=1.0)
    out = place(out, shell_drop(g, 0.0, 3, pan=0.5, length=1.6), 0.3, 0.5)
    export(D + '拳銃_3連射', out, drive=3)


def pistol_indoor():
    g = Gen(103)
    times = [0.0, 0.24]
    out = np.zeros(ns(0.7))
    for t0 in times:
        s = pistol_one(g, bright=1.15)
        i = ns(t0)
        out[i:i + len(s)] += s[:len(out) - i]
    out = space(out, indoor_ir(g, 0.8), wet=1.0)
    out = place(out, shell_drop(g, 0.0, 2, pan=-0.3, length=1.2), 0.3, 0.6)
    export(D + '拳銃_屋内2発', out, drive=3)


def revolver():
    g = Gen(104)
    # hammer cock
    cock = np.zeros(ns(0.45))
    cock = place(cock, mech_click(g, 2600, 0.5, 0.02), 0.0)
    cock = place(cock, mech_click(g, 4200, 0.35, 0.008), 0.11)
    cock = place(cock, thunk(g, 260, 0.02, 0.25), 0.115)
    dry = gunshot(g, cal=1.25, bright=0.9, boom=1.35, length=0.8, ring=1.6)
    seq = np.zeros(ns(1.4))
    seq = place(seq, cock, 0.0)
    seq = place(seq, dry, 0.42)
    out = space(seq, street_ir(g, 1.2, 2.8), wet=1.0)
    export(D + 'ヘビーピストル', out, drive=3)


def silenced():
    g = Gen(105)
    out = np.zeros(ns(0.9))
    for k, t0 in enumerate([0.0, 0.36]):
        n = ns(0.4)
        # suppressed: no crack, muffled "thup", slide dominates
        y = gunshot(g, cal=0.7, bright=0.25, boom=0.55, length=0.4, crack=0.08, ring=0.3, snap=0.1)
        y = lp(y, 1600) * 0.8
        puff = bp(g.r.standard_normal(n), 300, 2500) * env_ad(n, 0.002, 0.03) * 0.5
        y = y + puff
        y = place(y, mech_click(g, 3600, 0.55, 0.012), 0.008)
        y = place(y, thunk(g, 320, 0.02, 0.35), 0.035)
        y = place(y, mech_click(g, 2900, 0.3, 0.01), 0.04)
        out = place(out, y, t0)
    out = space(out, indoor_ir(g, 0.5), wet=0.35)
    out = place(out, shell_drop(g, 0.0, 2, pan=0.3, length=1.2), 0.25, 0.7)
    export(D + 'サプレッサー拳銃', out, -18)


def auto_burst(seed, name, rpm, count, cal, bright, ir_kind='street', target=-12, tail=2.5,
               jitter=0.006, shells=True, boom=1.0, ring=1.0):
    g = Gen(seed)
    dt = 60 / rpm
    times = [i * dt + g.u(-jitter, jitter) if i else 0 for i in range(count)]
    length = times[-1] + 0.6
    out = np.zeros(ns(length))
    for i, t0 in enumerate(times):
        s = gunshot(g, cal=g.jit(cal, 0.05), bright=g.jit(bright, 0.08), boom=g.jit(boom, 0.1),
                    length=0.6, ring=ring)
        s = place(s, mech_click(g, 3000, 0.08, 0.008), 0.01)
        # the first shot of a burst is a touch hotter, later ones heat up & blur
        s *= 1.0 if i == 0 else g.u(0.82, 0.95)
        i0 = ns(t0)
        e = min(len(out), i0 + len(s))
        out[i0:e] += s[:e - i0]
    ir = street_ir(g, 1.0, tail) if ir_kind == 'street' else (indoor_ir(g, 0.9) if ir_kind == 'indoor' else hall_ir(g, tail))
    out = space(out, ir, wet=1.0)
    if shells:
        out = place(out, shell_drop(g, 0.0, min(count, 8), pan=0.6, length=times[-1] + 1.5), 0.15, 0.4)
    export(D + name, out, drive=3)


def shotgun():
    g = Gen(110)
    dry = gunshot(g, cal=1.45, bright=0.85, boom=1.6, length=1.0, ring=0.7)
    # extra low "whump"
    n = len(dry)
    dry += sweep_sine(n, 110, 34, 0.06) * env_ad(n, 0.002, 0.16) * 0.5
    dry = sat(dry, 1.3)
    seq = np.zeros(ns(2.0))
    seq = place(seq, dry, 0.0)
    # pump: back (chk) + forward (chak), with plastic/wood slide noise
    for t0, f, a in [(0.62, 2200, 0.2), (0.82, 2900, 0.24)]:
        slide = bp(g.r.standard_normal(ns(0.09)), 600, 5000) * env_points(ns(0.09), [(0, 0), (0.02, 0.4), (0.09, 0)])
        seq = place(seq, slide * 0.12, t0 - 0.06)
        seq = place(seq, mech_click(g, f, a, 0.02, noise=0.8), t0)
        seq = place(seq, thunk(g, 210, 0.03, 0.2), t0 + 0.003)
    out = space(seq, street_ir(g, 1.1, 2.8), wet=1.0)
    shell = shell_drop(g, 0.0, 1, pan=0.6, length=1.0)
    out = place(out, lp(shell, 4000) * 1.3, 1.05, 0.6)  # plastic hull: duller
    export(D + 'ショットガン+ポンプ', out, drive=3)


def sniper():
    g = Gen(111)
    dry = gunshot(g, cal=1.75, bright=1.1, boom=1.7, length=1.2, crack=1.6, ring=0.8)
    n = len(dry)
    dry += sweep_sine(n, 90, 28, 0.08) * env_ad(n, 0.003, 0.22) * 0.55
    dry = sat(dry, 1.2)
    seq = np.zeros(ns(4.6))
    seq = place(seq, dry, 0.0)
    # bolt: lift, back, forward, down
    for t0, f, a in [(1.35, 2300, 0.14), (1.5, 2800, 0.18), (1.82, 3100, 0.2), (1.95, 2100, 0.16)]:
        seq = place(seq, mech_click(g, f, a, 0.018, noise=0.7), t0)
        seq = place(seq, thunk(g, 240, 0.025, 0.12), t0)
    ir = street_ir(g, 1.8, 4.0)
    out = space(seq, ir, wet=1.0)
    export(D + 'スナイパーライフル', out, drive=3)


def dry_fire():
    g = Gen(112)
    seq = np.zeros(ns(0.9))
    for t0 in [0.0, 0.45]:
        seq = place(seq, mech_click(g, 3800, 0.6, 0.012, noise=0.5), t0)
        seq = place(seq, mech_click(g, 2500, 0.25, 0.008), t0 + 0.012)
    out = space(seq, indoor_ir(g, 0.4), wet=0.18)
    export(D + '弾切れ_カチッ', out, -22)


def reload_pistol():
    g = Gen(113)
    seq = np.zeros(ns(1.7))
    # mag release + drop
    seq = place(seq, mech_click(g, 3000, 0.4, 0.01), 0.0)
    slide_out = bp(g.r.standard_normal(ns(0.12)), 1500, 7000) * env_points(ns(0.12), [(0, 0), (0.03, 0.5), (0.12, 0)])
    seq = place(seq, slide_out * 0.25, 0.02)
    # mag in: scrape then firm seat
    scrape = bp(g.r.standard_normal(ns(0.15)), 1200, 6000) * env_points(ns(0.15), [(0, 0), (0.12, 0.6), (0.15, 0)])
    seq = place(seq, scrape * 0.3, 0.55)
    seq = place(seq, thunk(g, 230, 0.03, 0.8), 0.7)
    seq = place(seq, mech_click(g, 2600, 0.5, 0.015, noise=0.9), 0.7)
    # slide rack back / release forward
    seq = place(seq, mech_click(g, 3300, 0.5, 0.012), 1.08)
    rack = bp(g.r.standard_normal(ns(0.08)), 2000, 8000) * env_points(ns(0.08), [(0, 0.5), (0.08, 0)])
    seq = place(seq, rack * 0.2, 1.08)
    seq = place(seq, mech_click(g, 2700, 0.8, 0.02, noise=0.8), 1.22)
    seq = place(seq, thunk(g, 280, 0.03, 0.6), 1.22)
    out = space(seq, indoor_ir(g, 0.4), wet=0.18)
    export(D + 'リロード_拳銃', out, -20)


def reload_rifle():
    g = Gen(114)
    seq = np.zeros(ns(2.2))
    seq = place(seq, mech_click(g, 2400, 0.4, 0.015), 0.0)
    # empty mag clatters on the floor
    clat = shell_drop(g, 0, 1, pan=0.2, length=0.6)[:, 0]
    seq = place(seq, lp(clat, 3500) * 0.5, 0.35)
    seq = place(seq, thunk(g, 150, 0.06, 0.6), 0.35)
    scrape = bp(g.r.standard_normal(ns(0.2)), 900, 5000) * env_points(ns(0.2), [(0, 0), (0.17, 0.6), (0.2, 0)])
    seq = place(seq, scrape * 0.3, 0.85)
    seq = place(seq, thunk(g, 190, 0.04, 0.9), 1.05)
    seq = place(seq, mech_click(g, 2300, 0.6, 0.02, noise=0.9), 1.05)
    # charging handle
    seq = place(seq, mech_click(g, 2900, 0.45, 0.015), 1.5)
    seq = place(seq, mech_click(g, 2500, 0.85, 0.03, noise=0.8), 1.66)
    seq = place(seq, thunk(g, 230, 0.04, 0.7), 1.66)
    out = space(seq, indoor_ir(g, 0.45), wet=0.2)
    export(D + 'リロード_ライフル', out, -19)


def smart_gun():
    """Smart weapon: lock-on chirps, then guided micro-rounds that hiss off."""
    g = Gen(120)
    seq = np.zeros(ns(2.4))
    # lock-on: three ascending chirps + confirm
    for i, (t0, f) in enumerate([(0.0, 1900), (0.12, 2250), (0.24, 2650)]):
        n = ns(0.06)
        tone = osc(f, n, 'square') * 0.25 + osc(f * 2, n, 'sine') * 0.2
        tone = lp(tone, 7000) * env_ad(n, 0.002, 0.02)
        seq = place(seq, tone * 0.25, t0)
    n = ns(0.18)
    conf = (osc(3200, n, 'sine') + 0.4 * osc(4800, n, 'sine')) * env_ad(n, 0.003, 0.06)
    seq = place(seq, conf * 0.25, 0.38)
    # 5-round burst
    t0 = 0.62
    for i in range(5):
        s = gunshot(g, cal=0.9, bright=1.15, boom=0.85, length=0.5, ring=0.6)
        # micro-rocket "fwip" that flies away to the right
        fw = whoosh(g, 0.35, 1500, 7000, peak_at=0.15, amp=0.25)
        s2 = np.zeros(ns(0.6))
        s2 = place(s2, s, 0)
        s2 = place(s2, fw, 0.006)
        seq = place(seq, s2, t0)
        t0 += 60 / 900 + g.u(-0.004, 0.004)
    out = space(seq, street_ir(g, 1.0, 2.3), wet=1.0)
    # guided rounds peel off with stereo motion
    for i in range(5):
        n = ns(0.5)
        trail = whoosh(g, 0.5, 2500, 9000, peak_at=0.2, amp=0.12)
        pan = np.linspace(0, g.u(-0.9, 0.9), n)
        out = place(out, autopan(trail, pan), 0.66 + i * 0.067)
    export(D + 'スマートガン_ロック射撃', out, drive=3)


def railgun():
    """Tech weapon: capacitor charge whine then electromagnetic discharge."""
    g = Gen(121)
    charge_t = 1.25
    n = ns(charge_t)
    t = tvec(n)
    f = 180 * (4000 / 180) ** ((t / charge_t) ** 1.6)
    whine = osc(f, n, 'saw') * 0.3 + osc(f * 1.5, n, 'sine') * 0.25 + osc(f * 0.5, n, 'sine') * 0.3
    whine = block_filter(whine, 600 + f * 2.2, 'lowpass', order=2)
    whine *= (t / charge_t) ** 1.3
    hiss = bp(g.r.standard_normal(n), 3000, 12000) * (t / charge_t) ** 3 * 0.25
    zaps = electric_arc(g, charge_t, 0.5, hum=False) * (t / charge_t) ** 2 * 0.35
    charge = whine + hiss + zaps
    # discharge
    shot = gunshot(g, cal=1.5, bright=1.3, boom=1.8, length=1.2, crack=1.8, ring=0.2)
    m = len(shot)
    tt = tvec(m)
    drop = osc(1600 * np.exp(-tt / 0.05) + 60, m, 'saw') * env_ad(m, 0.001, 0.12) * 0.4
    drop = lp(drop, 5000)
    ringing = modal(m, metal_modes(g, 520, 12, 0.5, bright=0.88)) * 0.12
    arcs = electric_arc(g, 1.2, 1.2, hum=False)[:m] * env_exp(m, 0.18) * 0.6
    shot = shot + drop + ringing + arcs
    seq = np.zeros(ns(charge_t + 4.0))
    seq = place(seq, charge, 0)
    seq = place(seq, shot, charge_t)
    out = space(seq, street_ir(g, 1.6, 3.5), wet=1.0)
    # heat-sink vent hiss after the shot
    vn = ns(1.3)
    venv = env_points(vn, [(0, 0), (0.15, 1), (1.3, 0)]) ** 2.5 * 0.5
    vent = bp(g.r.standard_normal(vn), 1800, 9000) * venv
    out = place(out, stereo(vent * 0.25, -0.3), charge_t + 0.6)
    vent2 = bp(g.r.standard_normal(vn), 1800, 9000) * venv
    out = place(out, stereo(vent2 * 0.25, 0.3), charge_t + 0.6)
    export(D + 'レールガン_チャージ射撃', out, drive=3)


def distant_firefight():
    """Gunfight a few blocks away: muffled, long city echoes (scene ambience)."""
    g = Gen(130)
    L = 9.0
    seq = np.zeros(ns(L + 0.8))
    t0 = 0.2
    while t0 < L - 0.5:
        kind = g.u()
        if kind < 0.45:  # single shots
            for k in range(int(g.u(1, 4))):
                s = gunshot(g, cal=g.u(0.8, 1.2), bright=0.6, length=0.6)
                seq = place(seq, s * g.u(0.3, 0.8), t0)
                t0 += g.u(0.15, 0.5)
        else:  # auto burst
            rpm = g.u(600, 900)
            for k in range(int(g.u(3, 9))):
                s = gunshot(g, cal=g.u(0.9, 1.1), bright=0.6, length=0.6)
                seq = place(seq, s * g.u(0.3, 0.7), t0)
                t0 += 60 / rpm
        t0 += g.u(0.4, 1.4)
    dry = lp(seq, 1700, 4)  # distance swallows the highs
    dry = peak(dry, 300, 0.8, 3)
    ir = street_ir(g, 3.0, 4.5)
    out = lp(space(dry, ir, wet=1.0, dry_gain=0.35, width=0), 3200, 2)
    export(D + '遠くの銃撃戦', out, -22)


JOBS = {
    'pistol_single': pistol_single, 'pistol_triple': pistol_triple, 'pistol_indoor': pistol_indoor,
    'revolver': revolver, 'silenced': silenced,
    'smg': lambda: auto_burst(106, 'SMG_連射', 1000, 7, 0.75, 1.1, target=-12, tail=2.2),
    'ar3': lambda: auto_burst(107, 'アサルトライフル_3点', 780, 3, 1.05, 1.0, target=-12, tail=2.6),
    'arfull': lambda: auto_burst(108, 'アサルトライフル_フルオート', 720, 14, 1.05, 1.0, target=-11, tail=2.8),
    'smg_in': lambda: auto_burst(109, 'SMG_屋内連射', 1000, 9, 0.75, 1.15, ir_kind='indoor', target=-12),
    'minigun': lambda: auto_burst(115, 'ミニガン_掃射', 2600, 46, 0.95, 0.95, target=-11, tail=3.0,
                                  jitter=0.0015, boom=0.8, ring=0.5),
    'shotgun': shotgun, 'sniper': sniper, 'dry_fire': dry_fire, 'reload_pistol': reload_pistol,
    'reload_rifle': reload_rifle, 'smart': smart_gun, 'rail': railgun, 'distant': distant_firefight,
}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
