"""02_被弾・着弾 / 03_爆発"""
import numpy as np

from dsp import (SR, Gen, ns, tvec, lp, hp, bp, peak, env_exp, env_ad, env_points, sweep_sine,
                 modal, metal_modes, sat, stereo, place, osc, block_filter, crackle, autopan,
                 bitcrush, doppler, compress, make_ir)
from master import export
from weapons import (gunshot, mech_click, thunk, whoosh, street_ir, indoor_ir, hall_ir, space,
                     electric_arc)

D2 = '02_被弾・着弾/'
D3 = '03_爆発/'


def close_room(g):
    return make_ir(g, rt60=0.35, predelay=0.002, early=[(g.u(0.002, 0.012), 0.25, 9000) for _ in range(6)],
                   lp_start=10000, lp_end=3000, tail_energy=0.25)


# ------------------------------------------------------------ building blocks
def flesh_hit(g, size=1.0, wet=1.0, bone=0.0):
    n = ns(0.6)
    t = tvec(n)
    # leading slap of the round going in
    slap = bp(g.r.standard_normal(n), 900, 5000) * env_ad(n, 0.0002, 0.003)
    # body thud
    thud = sweep_sine(n, 150 * g.u(0.9, 1.1), 55, 0.025) * env_ad(n, 0.001, 0.05 * size)
    thud += lp(g.r.standard_normal(n), 400) * env_ad(n, 0.001, 0.03) * 0.6
    # wet tissue: band-limited noise with fast random AM (liquid squelch)
    am = lp(np.abs(g.r.standard_normal(n)), 60)
    am /= am.max()
    sq = block_filter(g.r.standard_normal(n), 1400 * np.exp(-t / 0.08) + 350, 'bandpass', order=2, width=900)
    sq *= env_ad(n, 0.004, 0.07 * size) * (0.4 + am * 1.2)
    y = slap * 0.9 + thud * 1.4 + sq * 1.1 * wet
    if bone > 0:
        crk = crackle(g, n, 9000 * env_exp(n, 0.012), tau=0.0003, lo=1500, hi=9000)
        y += crk * bone * 1.8
    return sat(y, 1.6)


def metal_hit(g, f0, tau, amp=1.0, bright=0.85, count=14):
    n = ns(max(0.4, tau * 6))
    y = modal(n, metal_modes(g, f0, count, tau, bright=bright))
    y += hp(g.r.standard_normal(n), 1500) * env_ad(n, 0.0001, 0.003) * 1.2
    return y * amp


def debris(g, dur, density=900, lo=500, hi=7000, tau=0.0008, decay=0.15):
    n = ns(dur)
    dens = density * env_exp(n, decay)
    return crackle(g, n, dens, tau=tau, lo=lo, hi=hi)


def ricochet_whine(g, dur=0.7, f0=None, f1=None, pan_to=None):
    n = ns(dur)
    t = tvec(n)
    f0 = f0 or g.u(3200, 4300)
    f1 = f1 or g.u(900, 1400)
    f = f1 + (f0 - f1) * np.exp(-t / (dur * 0.45))
    f *= 1 + 0.012 * np.sin(2 * np.pi * g.u(25, 45) * t)  # tumbling bullet
    y = osc(f, n, 'sine') + 0.25 * osc(f * 2.01, n, 'sine')
    nz = block_filter(g.r.standard_normal(n), f, 'bandpass', order=2, width=600)
    y = y * 0.7 + nz * 0.9
    y *= env_ad(n, 0.004, dur * 0.35) * (1 + 0.3 * np.sin(2 * np.pi * g.u(25, 45) * t))
    pan_to = pan_to if pan_to is not None else g.u(-1, 1)
    return autopan(y, np.linspace(0, pan_to, n))


def whizby(g, dur=0.35, side=1):
    """Supersonic round passing close: snap + tearing hiss with doppler."""
    n = ns(dur)
    t = tvec(n)
    x = (t - dur * 0.35) * 700  # metres along the path
    dist = np.sqrt(x ** 2 + 2.0 ** 2)
    src = block_filter(g.r.standard_normal(n), 3500 + 2500 * np.exp(-np.abs(x) / 60), 'bandpass',
                       order=2, width=4000)
    y = src / dist * 4
    y += hp(g.r.standard_normal(n), 2000) * env_ad(n, 0.0001, 0.002, delay=dur * 0.35) * 1.2  # crack
    return autopan(y, np.clip(x / 40, -1, 1) * side)


# ------------------------------------------------------------ 02 hits
def flesh_variants():
    for i, (seed, size, bone) in enumerate([(201, 1.0, 0.0), (202, 1.2, 0.5), (203, 0.85, 0.0)], 1):
        g = Gen(seed)
        y = flesh_hit(g, size, bone=bone)
        out = space(y, close_room(g), wet=0.6, width=0.05)
        export(D2 + f'被弾_肉体{i}', out, -15)


def graze():
    g = Gen(204)
    n = ns(0.6)
    t = tvec(n)
    w = whizby(g, 0.3, 1)
    rip = bp(g.r.standard_normal(n), 1200, 6000) * env_ad(n, 0.001, 0.025)  # fabric + skin tear
    y = flesh_hit(g, 0.6, wet=0.5) * 0.6 + rip * 0.7
    out = np.zeros((ns(0.8), 2))
    out = place(out, w, 0)
    out = place(out, stereo(y, 0.2), 0.105)
    out = space(out, close_room(g), wet=0.5)
    export(D2 + '被弾_かすり傷', out, -15)


def armor_hit():
    """Round stopped by a ballistic plate: hard crack + dull body thump."""
    g = Gen(205)
    n = ns(0.6)
    crack = hp(g.r.standard_normal(n), 1200) * env_ad(n, 0.0001, 0.004) * 1.6
    plate = modal(n, metal_modes(g, 620, 10, 0.03, bright=0.75)) * 0.25  # ceramic/composite: short
    ceramic = debris(g, 0.6, 5000, 2000, 10000, tau=0.0002, decay=0.02) * 1.4
    thud = sweep_sine(n, 120, 50, 0.03) * env_ad(n, 0.002, 0.07) * 1.4
    y = sat(crack + plate + ceramic + thud, 1.5)
    out = space(y, close_room(g), wet=0.6)
    export(D2 + '被弾_防弾プレート', out, -15)


def cyber_hit():
    """Round hits cyberware: metallic clang, sparks, a hurt servo."""
    g = Gen(206)
    n = ns(1.6)
    t = tvec(n)
    clang = metal_hit(g, 780, 0.28, 1.0, bright=0.86)
    clang = np.pad(clang, (0, max(0, n - len(clang))))[:n]
    sparks = electric_arc(g, 1.6, 1.0, hum=False) * env_exp(n, 0.25) * 0.6
    # servo glitch: whine that stutters and drops
    f = 1100 * (1 - 0.5 * np.clip((t - 0.05) / 0.9, 0, 1)) + 40 * np.sin(2 * np.pi * 13 * t)
    servo = osc(f, n, 'saw') * 0.3
    servo = lp(servo, 5000)
    gate = (np.sin(2 * np.pi * 21 * t + 3 * np.sin(2 * np.pi * 3 * t)) > -0.2).astype(float)
    gate = lp(gate, 300)
    servo = bitcrush(servo, 6, 3) * gate * env_ad(n, 0.04, 0.35, delay=0.05) * 0.5
    thud = sweep_sine(n, 140, 60, 0.02) * env_ad(n, 0.001, 0.05)
    y = clang * 0.9 + sparks + servo + thud * 0.8
    out = space(y, close_room(g), wet=0.6)
    export(D2 + '被弾_サイバーウェア', out, -14)


def impact_concrete():
    g = Gen(207)
    out = np.zeros((ns(1.4), 2))
    for k, t0 in enumerate([0.0, 0.42]):
        n = ns(1.0)
        crack = hp(g.r.standard_normal(n), 800) * env_ad(n, 0.0001, 0.003) * 0.8
        thump = sweep_sine(n, 260, 90, 0.01) * env_ad(n, 0.0005, 0.025) * 0.8
        dbr = debris(g, 1.0, 1800, 600, 8000, tau=0.0006, decay=0.14) * 2.0
        dust = bp(g.r.standard_normal(n), 1500, 9000) * env_ad(n, 0.005, 0.12) * 0.12
        y = crack + thump + dbr + dust
        out = place(out, stereo(y, g.u(-0.5, 0.5)), t0)
    out = space(out, street_ir(g, 0.7, 1.5), wet=0.8)
    export(D2 + '着弾_コンクリート', out, -15)


def impact_metal():
    g = Gen(208)
    out = np.zeros((ns(1.8), 2))
    for k, (t0, f) in enumerate([(0.0, 1250), (0.33, 1580), (0.52, 1100)]):
        y = metal_hit(g, f, 0.22, 1.0, bright=0.88)
        y += sweep_sine(len(y), 300, 160, 0.01) * env_ad(len(y), 0.0005, 0.02) * 0.5
        out = place(out, stereo(y, g.u(-0.6, 0.6)), t0)
    out = space(out, street_ir(g, 0.7, 1.4), wet=0.7)
    export(D2 + '着弾_金属', out, -15)


def glass_break():
    g = Gen(209)
    L = 2.2
    out = np.zeros((ns(L), 2))
    n = ns(0.3)
    hit = hp(g.r.standard_normal(n), 1000) * env_ad(n, 0.0001, 0.006) * 1.4
    hit += modal(n, [(f, g.u(0.01, 0.04), g.u(0.3, 1)) for f in g.u(2500, 9000, 12)]) * 0.6
    out = place(out, stereo(hit), 0)
    # shards: many short glassy resonances, scattering then bouncing on the floor
    t0 = 0.002
    while t0 < 1.7:
        dens = np.exp(-t0 / 0.18) + 0.25 * np.exp(-((t0 - 0.55) / 0.2) ** 2)  # second wave = floor
        if g.u() < dens:
            m = ns(0.12)
            f = g.u(2800, 12000)
            shard = modal(m, [(f, g.u(0.008, 0.05), 1), (f * g.u(1.4, 2.7), g.u(0.005, 0.03), 0.5),
                              (f * g.u(2.8, 4.2), 0.01, 0.25)])
            shard += hp(g.r.standard_normal(m), 3000) * env_exp(m, 0.0006) * 0.3
            out = place(out, stereo(shard * g.u(0.15, 0.6) * (0.4 + dens), g.u(-0.8, 0.8)), t0)
        t0 += g.u(0.002, 0.012)
    n = ns(L)
    tinkle = crackle(g, n, 600 * env_exp(n, 0.4), tau=0.0002, lo=4000, hi=16000) * 0.6
    out += stereo(tinkle)
    out = space(out, indoor_ir(g, 0.7), wet=0.6)
    export(D2 + 'ガラス破砕', out, -14)


def ricochets():
    for i, seed in enumerate([210, 211], 1):
        g = Gen(seed)
        out = np.zeros((ns(1.4), 2))
        n = ns(0.2)
        hit = hp(g.r.standard_normal(n), 1500) * env_ad(n, 0.0001, 0.002) * 1.2
        hit += modal(n, metal_modes(g, g.u(1800, 2600), 8, 0.03)) * 0.4
        out = place(out, stereo(hit, g.u(-0.3, 0.3)), 0)
        out = place(out, ricochet_whine(g, g.u(0.55, 0.85)) * 0.8, 0.006)
        out = space(out, street_ir(g, 1.0, 1.8), wet=0.7)
        export(D2 + f'跳弾{i}', out, -16)


def whiz():
    g = Gen(212)
    out = np.zeros((ns(1.3), 2))
    for k, (t0, side) in enumerate([(0.0, 1), (0.21, -1), (0.47, 1)]):
        out = place(out, whizby(g, 0.32, side) * g.u(0.6, 1.0), t0)
    out = space(out, street_ir(g, 0.8, 1.5), wet=0.5)
    export(D2 + '弾がかすめる', out, -16)


def pinned_down():
    """Under fire behind cover: rounds smacking the cover around you."""
    g = Gen(213)
    L = 4.5
    out = np.zeros((ns(L + 1), 2))
    # remote shooter (muffled, a little away)
    t0 = 0.0
    times = []
    while t0 < L - 0.4:
        burst = int(g.u(3, 7))
        for k in range(burst):
            times.append(t0)
            t0 += 60 / 800 + g.u(-0.006, 0.006)
        t0 += g.u(0.35, 0.8)
    far = np.zeros(ns(L + 1))
    for tt in times:
        s = gunshot(g, cal=1.0, bright=0.7, length=0.5)
        far = place(far, s * 0.35, tt)
    far = lp(far, 4000)
    out += stereo(far, -0.4)[:len(out)]
    # each round lands ~ 80 ms later on cover near the listener
    for tt in times:
        r = g.u()
        land = tt + 0.08 + g.u(-0.01, 0.01)
        if r < 0.45:
            n = ns(0.7)
            y = hp(g.r.standard_normal(n), 800) * env_ad(n, 0.0001, 0.003) * 1.3
            y += debris(g, 0.7, 1200, 600, 8000, decay=0.1) * 1.1
            out = place(out, stereo(y, g.u(-0.8, 0.8)), land, g.u(0.5, 1))
        elif r < 0.7:
            y = metal_hit(g, g.u(900, 1800), 0.15, g.u(0.4, 0.8))
            out = place(out, stereo(y, g.u(-0.8, 0.8)), land)
        elif r < 0.85:
            out = place(out, whizby(g, 0.3, 1 if g.u() > 0.5 else -1) * 0.7, land - 0.1)
        else:
            out = place(out, ricochet_whine(g, g.u(0.4, 0.7)) * 0.4, land)
    out = space(out, street_ir(g, 1.0, 2.4), wet=1.0)
    export(D2 + '制圧射撃を受ける', out, -14)


# ------------------------------------------------------------ 03 explosions
def explosion_core(g, size=1.0, length=4.0):
    n = ns(length)
    t = tvec(n)
    y = np.zeros(n)
    # initial shock
    y += hp(g.r.standard_normal(n), 600) * env_ad(n, 0.0001, 0.004 * size) * 2.0
    # fireball roar: noise with collapsing brightness and a long body
    fc = 300 + 7000 * np.exp(-t / (0.05 * size))
    roar = block_filter(g.r.standard_normal(n), fc, 'lowpass', order=2, block=256)
    y += roar * env_ad(n, 0.002, 0.35 * size) * 2.2
    # sub boom
    y += sweep_sine(n, 90, 26, 0.12 * size) * env_ad(n, 0.004, 0.45 * size) * 1.8
    # rumble
    y += lp(g.brown(length), 160) * env_ad(n, 0.02, 0.9 * size) * 0.9
    y = sat(y, 2.2)
    k = ns(min(0.4, length / 4))
    y[-k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return y


def grenade():
    g = Gen(301)
    n = ns(0.9)
    # pin pull + spoon flick + bounce, then boom
    pre = np.zeros(ns(1.6))
    pre = place(pre, mech_click(g, 3600, 0.35, 0.01), 0.0)
    pre = place(pre, mech_click(g, 2400, 0.4, 0.03), 0.25)
    for k, (t0, a) in enumerate([(0.75, 0.6), (0.98, 0.35), (1.12, 0.2)]):
        pre = place(pre, metal_hit(g, 950, 0.04, a, bright=0.7), t0)
        pre = place(pre, thunk(g, 180, 0.03, a), t0)
    boom = explosion_core(g, 1.0, 5.0)
    d = debris(g, 3.0, 300, 300, 6000, tau=0.002, decay=0.8) * 0.9
    seq = np.zeros(ns(8))
    seq = place(seq, pre * 0.6, 0)
    seq = place(seq, boom, 1.6)
    seq = place(seq, d, 1.75)
    out = space(seq, street_ir(g, 1.6, 3.5), wet=1.0)
    export(D3 + '手榴弾_投擲から爆発', out, drive=4)


def big_explosion():
    """Vehicle / fuel explosion with burning tail."""
    g = Gen(302)
    boom = explosion_core(g, 1.7, 7.0)
    n = len(boom)
    second = explosion_core(g, 0.8, 3.0)
    seq = np.zeros(ns(11))
    seq = place(seq, boom, 0)
    seq = place(seq, second * 0.6, 0.38)
    # falling debris: metal panels and glass
    t0 = 0.6
    while t0 < 4.5:
        if g.u() < 0.6:
            seq = place(seq, metal_hit(g, g.u(300, 1200), g.u(0.05, 0.25), g.u(0.1, 0.5) * np.exp(-(t0 - 0.6) / 2)), t0)
        t0 += g.u(0.05, 0.3)
    seq = place(seq, debris(g, 4, 500, 400, 6000, tau=0.0015, decay=1.2) * 1.0, 0.3)
    # fire crackle bed that fades
    fn = ns(9)
    fire = crackle(g, fn, 250, tau=0.0015, lo=300, hi=5000) * 1.4
    fire += lp(g.brown(9), 500) * 0.25
    fire *= env_points(fn, [(0, 0), (1.0, 1), (5, 0.7), (9, 0)])
    seq = place(seq, fire, 1.0)
    out = space(seq, street_ir(g, 2.0, 4.5), wet=1.0)
    export(D3 + '大爆発_車両', out, drive=4)


def emp():
    g = Gen(303)
    L = 4.5
    n = ns(L)
    t = tvec(n)
    # charge-up hum
    pre = osc(55 * (1 + t * 2), n, 'saw') * env_points(n, [(0, 0), (0.6, 0.4), (0.7, 0)]) * 0.5
    pre = lp(pre, 2000)
    # pulse: bass drop + rising/falling zap, then electronics dying (crackle and falling whines)
    m = ns(L - 0.7)
    tt = tvec(m)
    drop = sweep_sine(m, 220, 30, 0.15) * env_ad(m, 0.002, 0.6) * 1.4
    zap = osc(3000 * np.exp(-tt / 0.08) + 80, m, 'saw') * env_ad(m, 0.001, 0.3) * 0.35
    zap = lp(zap, 9000)
    wave = block_filter(g.r.standard_normal(m), 200 + 6000 * np.exp(-tt / 0.15), 'lowpass') * env_ad(m, 0.002, 0.5)
    arcs = electric_arc(g, L - 0.7, 1.3, hum=False) * env_exp(m, 0.4) * 0.8
    dying = np.zeros(m)
    for k in range(5):
        f0 = g.u(800, 3000)
        d = ns(g.u(0.6, 1.8))
        tone = osc(f0 * np.exp(-tvec(d) / g.u(0.2, 0.6)) + 30, d, 'square') * env_ad(d, 0.01, 0.4) * 0.06
        dying = place(dying, lp(tone, 6000), g.u(0.1, 0.5))
    body = drop + zap + wave * 0.9 + arcs + dying
    seq = np.zeros(n + ns(2))
    seq = place(seq, pre, 0)
    seq = place(seq, body, 0.7)
    out = space(seq, street_ir(g, 1.2, 2.8), wet=0.8)
    export(D3 + 'EMPグレネード', out, drive=3)


def flashbang():
    g = Gen(304)
    L = 7.0
    n = ns(L)
    t = tvec(n)
    bang = explosion_core(g, 0.5, 2.0)
    bang += hp(g.r.standard_normal(ns(2.0)), 2000) * env_ad(ns(2.0), 0.0001, 0.01) * 1.5
    bang = space(bang, indoor_ir(g, 0.9), wet=1.0)
    # the listener is deafened: everything after the bang is muffled + tinnitus
    k = ns(0.03)
    muffle = np.zeros_like(bang)
    for ch in range(2):
        a = bang[:, ch]
        muffle[:, ch] = np.concatenate([a[:k], lp(a[k:], 600, 4) * 0.8])
    out = np.zeros((n, 2))
    out[:len(muffle)] += muffle[:n]
    ring_env = env_points(n, [(0, 0), (0.05, 1), (2.5, 0.6), (L, 0)]) ** 1.5
    ring = (osc(3950, n, 'sine') + 0.2 * osc(3950 * 1.002, n, 'sine')) * ring_env * 0.18
    out += np.stack([ring, ring * 0.92], 1)
    export(D3 + '閃光弾_耳鳴り', out, drive=2)


JOBS = {
    'flesh': flesh_variants, 'graze': graze, 'armor': armor_hit, 'cyber': cyber_hit,
    'concrete': impact_concrete, 'metal': impact_metal, 'glass': glass_break, 'rico': ricochets,
    'whiz': whiz, 'pinned': pinned_down, 'grenade': grenade, 'big': big_explosion, 'emp': emp,
    'flash': flashbang,
}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
