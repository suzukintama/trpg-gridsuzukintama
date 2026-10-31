"""Version 5: built on the newly collected raw recordings (rec/inbox, all CC0).
Run after gen_v3.py and gen_v4.py; same names are overwritten, new ones added.

Raw recordings are used as they are: cut, level, fade, and placed in sequence.
"""
import numpy as np

from dsp import SR, ns, env_points, seamless
from master import export
from gen_rec import load
from gen_v3 import S, gun, kn, lv, pan, seq, D1, D2, D3, D4, D5, D6, D7
from segs import shots, onsets, cut

IB = 'inbox/'


def raw(rel):
    y = load(IB + rel, mono=False)
    return y / (np.max(np.abs(y)) + 1e-12)


def shot_list(rel, gap=0.35, maxlen=4.0):
    return [s for _, _, s in shots(raw(rel), gap=gap, maxlen=maxlen)]


def window(y, dur, center=None):
    """dur seconds around the loudest moment (or around `center` s)."""
    n = ns(dur)
    if len(y) <= n:
        return y
    if center is None:
        e = np.convolve(np.mean(y ** 2, axis=1), np.ones(ns(0.5)) / ns(0.5), mode='same')
        c = int(np.argmax(e))
    else:
        c = ns(center)
    a = int(np.clip(c - n // 2, 0, len(y) - n))
    return y[a:a + n]


def seg(rel, t0, t1, fade=0.3):
    return cut(raw(rel), t0, t1, pre=0.0, fade=fade)


def soft(y, fin=0.3, fout=0.6):
    n = len(y)
    return y * env_points(n, [(0, 0), (fin, 1), (n / SR - fout, 1), (n / SR, 0)])[:, None]


# ================================================================ 01 guns
def guns():
    # pistol: Walther PPQ singles with their full outdoor tails
    p = shot_list('firearm_library/walther-ppq-X_39P.flac')
    p = [cut(x, 0, 2.4, pre=0, fade=0.4) for x in p]
    export(D1 + '拳銃_単発', p[0], drive=1)
    export(D1 + '拳銃_3点バースト', seq([(i * 0.085, p[i % 3] * (1 if i == 0 else 0.92)) for i in range(3)]), drive=1)
    from dsp import Gen
    g = Gen(5101)
    parts, t = [], 0.0
    for i in range(15):
        parts.append((t, p[i % 3] * (1 if i == 0 else g.u(0.88, 0.97))))
        t += g.u(0.16, 0.24) + (0.45 if i == 7 else 0.0)
    export(D1 + '拳銃_15連射', seq(parts), drive=1)
    groups = [2, 3, 1, 4, 2, 1, 3, 5, 2, 1, 3, 2, 4, 1, 2, 3]
    parts, t, k = [], 0.1, 0
    for n in groups:
        for j in range(n):
            parts.append((t, p[k % 3] * g.u(0.88, 1.0)))
            k += 1
            t += g.u(0.15, 0.22)
        t += g.u(0.5, 1.3)
    L = float(np.ceil(t + 2.0))
    y = seq(parts, length=L + 3)
    # fold the tail that runs past the loop end back onto the start, so the loop is seamless
    head = y[:ns(L)].copy()
    tail = y[ns(L):]
    head[:len(tail)] += tail
    export(D1 + '拳銃_撃ち続けループ', head, drive=1, loop=True, ogg=True)

    h = shot_list('firearm_library/1911-A_42P.flac')
    export(D1 + 'ヘビーピストル', seq([(0, kn('metalClick', 0.3)), (0.12, kn('metalLatch', 0.25)),
                                    (0.45, h[0][:ns(3.0)])]), drive=1)
    ar = shot_list('firearm_library/ar-15-D_32P.flac')
    export(D1 + 'アサルトライフル_単発', ar[0][:ns(3.2)], drive=1)
    export(D1 + 'アサルトライフル_3点', seq([(i * 60 / 700, ar[i % 2][:ns(3.0)] * (1 if i == 0 else 0.92)) for i in range(3)]),
           drive=1)
    export(D1 + 'アサルトライフル_フルオート', shot_list('firearm_library/ak-47-C_27P.flac')[0], drive=1)
    export(D1 + 'SMG_連射', shot_list('firearm_library/carl-gustav-m45-G_24P.flac')[0], drive=1)
    export(D1 + 'サブマシンガン_長連射', shot_list('firearm_library/ppsh-P_34P.flac')[0], drive=1)
    export(D1 + 'ショットガン', shot_list('firearm_library/nova-O_21P.flac')[0], drive=1)
    export(D1 + 'ショットガン+ポンプ', seq([(0, shot_list('firearm_library/nova-O_21P.flac')[0][:ns(1.0)]),
                                          (0.95, gun('pump', 0.3)), (1.6, gun('shell-2', 0.2))]), drive=1)
    rl = gun('reload')
    sn = shot_list('firearm_library/tikka-W_29P.flac')[0]
    export(D1 + 'スナイパーライフル', seq([(0, sn), (2.6, rl[ns(0.85):ns(1.3)] * 0.3)]), drive=1)
    export(D1 + 'ミニガン_掃射', soft(raw('minigun/minigun-gatling-close-03.mp3'), 0.01, 0.4), drive=1)
    ip = shot_list('indoor_gun/indoor-gun-range-pistol-02.mp3')
    export(D1 + '拳銃_屋内', ip[0], drive=1)
    export(D1 + 'ライフル_屋内', shot_list('indoor_gun/indoor-gun-ar15-room-03.mp3')[0], drive=1)
    export(D1 + 'サプレッサー拳銃', raw('suppressed/suppressed-p226-02.mp3'), -18, max_gr=6)
    export(D1 + 'サプレッサーSMG', raw('suppressed/suppressed-smg-04.mp3'), -17, max_gr=6)
    export(D1 + 'サプレッサー狙撃銃', raw('suppressed/suppressed-tac50-03.mp3'), -16, max_gr=6)
    export(D1 + '薬莢_落下', soft(seg('casings/casings-brass-concrete-01.mp3', 0.0, 4.0), 0.01, 0.4), -20, max_gr=6)


# ================================================================ 02 hits
def hits():
    # flesh: real meat hits (slapped / pounded meat), one layer only
    export(D2 + '被弾_肉体1', raw('bullet_flesh/bullet-flesh-meat-slap-03.mp3'), -15, max_gr=6)
    pm = raw('bullet_flesh/bullet-flesh-pound-meat-02.mp3')
    hits_ = [cut(pm, t, t + 0.35, fade=0.1) for t in onsets(pm)[:40]]
    best = sorted(hits_, key=lambda s: -np.sqrt(np.mean(s ** 2)))
    export(D2 + '被弾_肉体2', seq([(0, best[0]), (0.004, lv('wet_slime_09', 0.35))]), -15, max_gr=6)
    export(D2 + '被弾_肉体3', best[1], -15, max_gr=6)
    # a real round on a steel plate: the hit and its long ring
    st = raw('bullet_metal/bullet-metal-steel-plate-01.mp3')
    sh = shots(st, gap=0.35, maxlen=4.0)
    plate = sh[0][2][:ns(2.5)]
    plate2 = sh[1][2][:ns(1.3)] if len(sh) > 1 else plate
    export(D2 + '被弾_サイバーウェア1', plate, -15, max_gr=6)
    export(D2 + '着弾_金属', seq([(0, plate), (0.9, pan(plate2, 0.4))]), -16, max_gr=6)


# ================================================================ 04 melee / cyberware body
def body():
    export(D4 + '義体_サーボ駆動', soft(window(raw('servo/servo-motor-03.mp3'), 3.0), 0.05, 0.3), -18)
    export(D4 + '義体_排気', raw('pneumatic/pneumatic-rig-air-release-01.mp3'), -17)
    sv = soft(window(raw('servo/servo-sg90-close-02.mp3'), 0.9), 0.05, 0.15) * 0.5
    export(D4 + 'アームブレード展開', seq([(0, sv), (0.85, lv('mech_SpringLoadedBlade2')),
                                     (0.89, lv('knife_SmallKnifeUnsheath1', 0.5))]), -15, max_gr=6)


# ================================================================ 05 netrunning / electric
def electric():
    export(D5 + 'ショート_感電', soft(window(raw('spark/spark-130kv-short-02.mp3'), 2.5), 0.005, 0.4), -15, max_gr=6)
    export(D5 + '火花_スパーク', soft(window(raw('spark/spark-35kv-sparks-01.mp3'), 3.0), 0.02, 0.4), -17, max_gr=6)
    export(D5 + '電撃_アーク放電', soft(window(raw('spark/spark-jacobs-ladder-03.mp3'), 4.0), 0.05, 0.5), -17, max_gr=6)
    export(D5 + 'ハッキング_タイピング', soft(window(raw('keyboard/keyboard-fast-03.mp3'), 6.0), 0.1, 0.5), -19, max_gr=9)


# ================================================================ 06 machines / vehicles / city
def machines():
    export(D6 + 'パトカーサイレン通過', soft(window(raw('siren/siren-police-pass-01.mp3'), 22.0), 1.0, 2.0), -17)
    export(D6 + 'ヘリ_頭上通過', soft(window(raw('flyby/flyby-heli-overhead-04.mp3'), 20.0), 1.5, 3.0), -16)
    export(D6 + 'ジェット機_通過', soft(window(raw('flyby/flyby-jet-f18-02.mp3'), 16.0), 1.0, 3.0), -15)
    export(D6 + '電気自動車_通過', soft(raw('ev_car/ev-car-leaf-pass-01.mp3'), 0.5, 1.0), -18)
    export(D6 + 'ドローン通過', soft(window(raw('drone/drone-mavic2-flyby-01.mp3'), 16.0), 1.5, 2.5), -18)
    dm = raw('drone/drone-mavic-mini-03.mp3')
    export(D6 + 'ドローン_ホバリング', seamless(dm[ns(1.0):ns(1.0 + 30.0)], 26.0, 4.0), -20, loop=True, ogg=True)
    export(D6 + '自動ドア_開', soft(seg('pneumatic/pneumatic-emu-door-hiss-03.mp3', 0.0, 11.0, fade=0.8), 0.02, 0.8), -18)
    export(D6 + '自販機_購入', raw('vending/vending-coke-machine-01.mp3'), -18, max_gr=6)
    export(D6 + '蒸気_噴出', raw('steam/steam-safety-valve-02.mp3'), -18)
    export(D6 + 'ネオン_点灯', soft(raw('neon/neon-flicker-on-04.mp3'), 0.05, 1.0), -20, max_gr=6)
    export(D6 + '足音_コンクリート', soft(window(raw('footsteps/footsteps-concrete-light-01.mp3'), 8.0), 0.2, 0.6), -20, max_gr=10)
    export(D6 + '足音_金属グレーチング', soft(window(raw('footsteps/footsteps-metal-grate-03.mp3'), 8.0), 0.2, 0.6), -19, max_gr=9)
    export(D6 + '足音_金属階段', soft(window(raw('footsteps/footsteps-metal-stairs-04.mp3'), 10.0), 0.2, 0.6), -19, max_gr=6)


# ================================================================ 07 ambience loops on the new recordings (no gunshots)
LR, XR = 54.0, 4.0
T = LR + XR


def bed(rel, start=0.0, gain=1.0):
    y = load(IB + rel, mono=False)[ns(start):]
    y = y / (np.sqrt(np.mean(y ** 2)) + 1e-12)
    if len(y) < ns(T):
        X = min(ns(1.5), len(y) // 4)
        src = y.copy()
        while len(y) < ns(T):
            t = np.linspace(0, 1, X)[:, None]
            y = np.concatenate([y[:-X], y[-X:] * np.cos(t * np.pi / 2) + src[:X] * np.sin(t * np.pi / 2), src[X:]])
    return y[:ns(T)] * gain


def put(y, t0, s):
    i = ns(t0)
    y[i:i + len(s)] += s[:len(y) - i]
    return y


def ambience():
    # rain on a neon street: city rain, the gutter, a real neon sign's buzz, one roll of thunder
    y = (bed('rain_city/rain-city-strong-street-02.mp3', 0, 0.55) + bed('rain_city/rain-city-backstreet-gutter-03.mp3', 20, 0.2) +
         bed('neon/neon-sign-buzz-01.mp3', 0, 0.05))
    th = load('amb/thunder_distant.ogg', mono=False)
    y = put(y, 28.0, th / np.max(np.abs(th)) * 0.35)
    export(D7 + '雨のネオン街', seamless(y, LR, XR), -20, loop=True, ogg=True)
    # nightlife street: a real night street, electric cars going by, a neon tube
    y = bed('street_night/street-night-vancouver-02.mp3', 30, 0.8) + bed('neon/neon-fluorescent-old-02.mp3', 0, 0.04)
    ev = raw('ev_car/ev-car-pass-02.mp3')
    for t0, p in [(12.0, -0.5), (33.0, 0.5)]:
        y = put(y, t0, pan(ev / np.sqrt(np.mean(ev ** 2)) * 0.25, p))
    export(D7 + '夜の繁華街', seamless(y, LR, XR), -20, loop=True, ogg=True)
    # back alley: a quiet night street, a buzzing fluorescent tube, steam, the rooftop AC
    y = (bed('street_night/street-night-lisbon-03.mp3', 10, 0.7) + bed('neon/neon-fluorescent-old-02.mp3', 10, 0.08) +
         bed('steam/steam-pipe-valve-beijing-03.mp3', 0, 0.12))
    export(D7 + '裏路地', seamless(y, LR, XR), -22, loop=True, ogg=True)
    # rainy back alley
    y = bed('rain_city/rain-city-downpipe-04.mp3', 60, 0.6) + bed('rain_city/rain-city-light-street-01.mp3', 0, 0.35)
    export(D7 + '雨の路地裏', seamless(y, LR, XR), -21, loop=True, ogg=True, max_gr=6)


JOBS = {'guns': guns, 'hits': hits, 'body': body, 'electric': electric, 'machines': machines, 'ambience': ambience}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
