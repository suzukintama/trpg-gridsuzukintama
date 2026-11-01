"""Version 6: finished sounds cut from the CC0 recordings in rec/inbox/ (see rec/inbox/CREDITS.md).

Three kinds of treatment, nothing synthetic:
  - one-shots: the recording is cut to the event itself (a few ms before the onset, a natural
    tail, then a fade), so the background noise before and after the event is gone
  - pass-bys (siren, jet, helicopter, drone, car): the loudest stretch, capped in length, long fades
  - ambience: a seamless loop (54 s unless the recording is shorter)
Runs on top of gen_v5.py; the names here are all new.
"""
import numpy as np

from dsp import SR, ns, seamless
from master import export
from gen_rec import load

D1, D2, D5, D6, D7 = '01_銃/', '02_被弾・着弾/', '05_ハッキング/', '06_機械・乗り物/', '07_環境音ループ/'
HOP = ns(0.01)


def rec(rel):
    y = load(f'inbox/{rel}', mono=False)
    return y / (np.max(np.abs(y)) + 1e-12)


def env_db(y):
    m = y.mean(axis=1)
    n = len(m) // HOP
    r = np.sqrt(np.mean(m[:n * HOP].reshape(n, HOP) ** 2, axis=1))
    return 20 * np.log10(r + 1e-9)


def segments(y, merge=0.3, rel_thr=30, abs_thr=12):
    """[(start_s, end_s, peak_db)] of the stretches that stand out of the background."""
    db = env_db(y)
    floor, top = np.percentile(db, 10), np.max(db)
    thr = max(top - rel_thr, floor + abs_thr)
    act = db > thr
    segs, i, n = [], 0, len(db)
    while i < n:
        if not act[i]:
            i += 1
            continue
        j = i
        while j < n and (act[j] or np.any(act[j:j + int(merge * 100)])):
            j += 1
        segs.append([i * 0.01, j * 0.01, float(np.max(db[i:j]))])
        i = j
    return segs


def tail_end(y, start_s, floor_db, tail_db=8.0, tail_max=2.5):
    """Where the sound after start_s has decayed into the background (seconds)."""
    db = env_db(y)
    i, lim = int(start_s * 100), min(len(db), int((start_s + tail_max) * 100))
    quiet = 0
    while i < lim:
        quiet = quiet + 1 if db[i] < floor_db + tail_db else 0
        if quiet >= 8:
            return (i - 8) * 0.01
        i += 1
    return lim * 0.01


def cut(y, idx=0, pre=0.03, tail_max=2.5, tail_db=8.0, merge=0.3, fout=None, order='time'):
    """The idx-th event of a recording (by time, or by level with order='level'), cut clean."""
    segs = segments(y, merge=merge)
    if order == 'level':
        segs = sorted(segs, key=lambda s: -s[2])
    s0, s1, _ = segs[idx]
    floor = np.percentile(env_db(y), 10)
    e = max(s1, tail_end(y, s1, floor, tail_db, tail_max))
    a, b = max(0, ns(s0 - pre)), min(len(y), ns(e))
    out = y[a:b].copy()
    f = ns(fout if fout is not None else min(0.25, (e - s1) / 2 + 0.03))
    f = min(f, len(out) // 2)
    if f > 0:
        out[-f:] *= np.cos(np.linspace(0, np.pi / 2, f))[:, None] ** 2
    k = ns(0.004)
    out[:k] *= np.linspace(0, 1, k)[:, None]
    return out


def window(y, t0, dur, fin=0.3, fout=0.5):
    out = y[ns(t0):ns(t0 + dur)].copy()
    a, b = ns(fin), ns(fout)
    out[:a] *= np.sin(np.linspace(0, np.pi / 2, a))[:, None] ** 2
    out[-b:] *= np.cos(np.linspace(0, np.pi / 2, b))[:, None] ** 2
    return out


def passby(y, cap=25.0, below=35.0, fade=1.5, pad=0.8):
    """The loud stretch of a pass-by, centred on the peak, capped at cap seconds."""
    db = env_db(y)
    top, pk = np.max(db), int(np.argmax(db))
    act = np.nonzero(db > top - below)[0]
    s, e = act[0] * 0.01 - pad, act[-1] * 0.01 + pad
    if e - s > cap:
        c = pk * 0.01
        s, e = c - cap / 2, c + cap / 2
        if s < 0:
            s, e = 0, cap
        if e > len(y) / SR:
            e, s = len(y) / SR, len(y) / SR - cap
    s, e = max(0.0, s), min(len(y) / SR, e)
    return window(y, s, e - s, fade, fade)


def loop(y, t0, L=54.0, X=4.0):
    avail = len(y) / SR - t0
    if avail < L + X:
        L = float(np.floor(avail - X))
    return seamless(y[ns(t0):], L, X), L


# ================================================================ 01 guns (Free Firearm Sound Library, near / mid mics)
def guns():
    fl = lambda n: rec(f'firearm_library/{n}.flac')
    # near mics: the shooter's own gun
    export(D1 + '1911_単発', cut(fl('1911-A_42P')), drive=1)
    x = fl('1911-A_42P')
    a, b = cut(x, 0), cut(x, 1)
    two = np.zeros((ns(0.18) + len(b), 2))
    two[:len(a)] += a
    two[ns(0.18):] += b * 0.95
    export(D1 + '1911_2連射', two, drive=1)
    export(D1 + 'ワルサーPPQ_単発', cut(fl('walther-ppq-X_39P')), drive=1)
    export(D1 + 'AR15_単発', cut(fl('ar-15-D_32P')), drive=1)
    export(D1 + 'AK47_単発', cut(fl('ak-47-C_28P')), drive=1)
    export(D1 + 'AK47_短連射', cut(fl('ak-47-C_29P')), drive=1)
    export(D1 + 'AK47_長連射', cut(fl('ak-47-C_27P')), drive=1)
    export(D1 + 'M45_SMG_単発', cut(fl('carl-gustav-m45-G_31P')), drive=1)
    export(D1 + 'M45_SMG_短連射', cut(fl('carl-gustav-m45-G_33P')), drive=1)
    export(D1 + 'M45_SMG_長連射', cut(fl('carl-gustav-m45-G_35P')), drive=1)
    export(D1 + 'PPSh_単発', cut(fl('ppsh-P_30P')), drive=1)
    export(D1 + 'PPSh_短連射', cut(fl('ppsh-P_32P')), drive=1)
    export(D1 + 'PPSh_長連射', cut(fl('ppsh-P_34P')), drive=1)
    export(D1 + 'ショットガン_Nova', cut(fl('nova-O_21P')), drive=1)
    export(D1 + 'ショットガン_M12', cut(fl('model-12-K_22P')), drive=1)
    export(D1 + 'モシンナガン_単発', cut(fl('mosin-nagant-M_21P')), drive=1)
    export(D1 + 'ティッカ_狙撃', cut(fl('tikka-W_29P')), drive=1)
    # mid mics: the same guns heard from a few metres in front
    export(D1 + '拳銃_中距離', cut(fl('1911-A_34P'), tail_max=3.0), drive=1)
    export(D1 + 'ライフル_中距離', cut(fl('ar-15-D_24P'), tail_max=3.0), drive=1)
    export(D1 + 'AK47連射_中距離', cut(fl('ak-47-C_36P'), tail_max=3.0), drive=1)
    export(D1 + 'ショットガン_中距離', cut(fl('model-12-K_17P'), tail_max=3.0), drive=1)
    export(D1 + '狙撃銃_中距離', cut(fl('tikka-W_24P'), tail_max=3.0), drive=1)
    export(D1 + 'SMG連射_中距離', cut(fl('carl-gustav-m45-G_24P'), tail_max=3.0), drive=1)


# ================================================================ 01 guns: suppressed / indoors / minigun / casings (Freesound)
def guns2():
    export(D1 + '消音拳銃_単発', cut(rec('suppressed/suppressed-p226-02.mp3'), tail_max=0.5), drive=1)
    export(D1 + '消音拳銃_3連射', window(rec('suppressed/suppressed-p226-02.mp3'), 0.05, 2.1, 0.005, 0.2), drive=1)
    export(D1 + '消音SMG_連射', window(rec('suppressed/suppressed-smg-04.mp3'), 0.02, 2.6, 0.005, 0.3), drive=1)
    export(D1 + '消音狙撃銃', window(rec('suppressed/suppressed-tac50-03.mp3'), 0.0, 3.2, 0.005, 0.6), drive=1)
    export(D1 + '消音FNX45_単発', rec('suppressed/suppressed-fnx45-osprey-01.mp3'), drive=1)
    export(D1 + '屋内射場_ライフル', cut(rec('indoor_gun/indoor-gun-range-hk416-01.mp3'), tail_max=2.0), drive=1)
    export(D1 + '屋内射場_拳銃', cut(rec('indoor_gun/indoor-gun-range-pistol-02.mp3'), tail_max=0.9), drive=1)
    export(D1 + '屋内射場_拳銃5連', window(rec('indoor_gun/indoor-gun-range-pistol-02.mp3'), 0.1, 6.0, 0.005, 0.5), drive=1)
    export(D1 + '室内_AR15_単発', cut(rec('indoor_gun/indoor-gun-ar15-room-03.mp3'), tail_max=2.0), drive=1)
    export(D1 + 'ミニガン_至近', window(rec('minigun/minigun-gatling-close-03.mp3'), 0.0, 7.6, 0.005, 0.4), drive=1)
    export(D1 + 'ミニガン_M134', window(rec('minigun/minigun-m134-demo-01.mp3'), 8.0, 6.0, 0.05, 0.8), drive=1)
    export(D1 + 'ミニガン_遠方', window(rec('minigun/minigun-m134-200ft-02.mp3'), 0.3, 8.0, 0.05, 1.0), drive=1)
    export(D1 + '薬莢_1個_コンクリ', cut(rec('casings/casings-brass-concrete-01.mp3'), tail_max=0.8, merge=0.15), -20, max_gr=6)
    export(D1 + '薬莢_ばらまき', window(rec('casings/casings-brass-concrete-01.mp3'), 1.8, 3.0, 0.005, 0.4), -20, max_gr=6)
    export(D1 + '薬莢_1個_タイル', cut(rec('casings/casings-tile-mixed-03.mp3'), tail_max=1.0, merge=0.15), -20, max_gr=6)
    export(D1 + '薬莢_数個_タイル', window(rec('casings/casings-tile-mixed-03.mp3'), 2.4, 2.5, 0.005, 0.4), -20, max_gr=6)


# ================================================================ 02 hits
def hits():
    sp = rec('bullet_metal/bullet-metal-steel-plate-01.mp3')
    for i in range(3):
        export(D2 + f'着弾_鋼板{i + 1}', cut(sp, i, tail_max=3.0), -16, max_gr=6)
    export(D2 + '被弾_肉_湿った音', rec('bullet_flesh/bullet-flesh-meat-slap-03.mp3'), -15, max_gr=6)
    pm = rec('bullet_flesh/bullet-flesh-pound-meat-02.mp3')
    tpk = int(np.argmax(env_db(pm))) * 0.01
    export(D2 + '被弾_肉塊', window(pm, tpk - 0.02, 0.4, 0.003, 0.15), -15, max_gr=6)
    export(D2 + '被弾_鈍い打撃', cut(rec('bullet_flesh/bullet-flesh-punch-dough-01.mp3'), 0, tail_max=0.6, merge=0.2, order='level'),
           -15, max_gr=6)


# ================================================================ 05 electricity / light
def electric():
    export(D5 + '放電_35kV', window(rec('spark/spark-35kv-sparks-01.mp3'), 0.0, 3.0, 0.005, 0.4), -18)
    export(D5 + '短絡_130kV', window(rec('spark/spark-130kv-short-02.mp3'), 0.0, 4.0, 0.01, 0.6), -16)
    export(D5 + 'ヤコブの梯子', window(rec('spark/spark-jacobs-ladder-03.mp3'), 2.0, 4.0, 0.2, 0.6), -18)
    export(D5 + '溶接アーク', window(rec('spark/spark-arc-welding-04.mp3'), 1.0, 4.0, 0.05, 0.5), -18)
    export(D5 + 'ネオン管_点灯', window(rec('neon/neon-flicker-on-04.mp3'), 1.8, 5.0, 0.01, 1.0), -20)
    export(D5 + '蛍光灯_点灯', window(rec('neon/neon-fluorescent-warmup-03.mp3'), 7.5, 7.0, 0.01, 1.2), -20)


# ================================================================ 06 machines and vehicles
def machines():
    export(D6 + 'サイレン_通過1', passby(rec('siren/siren-police-pass-01.mp3'), cap=25), -18)
    export(D6 + 'サイレン_通過2', passby(rec('siren/siren-police-pass-02.mp3'), cap=25), -18)
    export(D6 + 'サイレン_至近通過', passby(rec('siren/siren-police-pass-fr-03.mp3'), cap=25), -18)
    export(D6 + 'ジェット機_通過1', passby(rec('flyby/flyby-jet-f18-01.mp3'), cap=25), -18)
    export(D6 + 'ジェット機_通過2', passby(rec('flyby/flyby-jet-f18-02.mp3'), cap=25), -18)
    export(D6 + 'ヘリ_至近通過', passby(rec('flyby/flyby-heli-close-03.mp3'), cap=30), -18)
    export(D6 + 'ヘリ_真上通過', passby(rec('flyby/flyby-heli-overhead-04.mp3'), cap=30), -18)
    export(D6 + 'ドローン通過_大型', passby(rec('drone/drone-mavic2-flyby-01.mp3'), cap=20), -18)
    export(D6 + 'ドローン通過_高速', passby(rec('drone/drone-quad-flyby-02.mp3'), cap=20), -18)
    export(D6 + 'ドローン通過_小型', passby(rec('drone/drone-mavic-mini-03.mp3'), cap=20), -18)
    export(D6 + 'EV通過1', passby(rec('ev_car/ev-car-leaf-pass-01.mp3'), cap=12, fade=0.8), -18)
    export(D6 + 'EV通過2', passby(rec('ev_car/ev-car-pass-02.mp3'), cap=12, fade=0.8), -18)
    export(D6 + 'EVバン_通過', passby(rec('ev_car/ev-car-van-pass-03.mp3'), cap=14, fade=0.8), -18)
    export(D6 + 'サーボ_1動作', cut(rec('servo/servo-sg90-close-02.mp3'), tail_max=0.4, merge=0.25), -20)
    export(D6 + 'サーボ_連続動作', window(rec('servo/servo-motor-03.mp3'), 1.3, 4.0, 0.05, 0.4), -20)
    export(D6 + 'アクチュエータ', cut(rec('servo/servo-linear-actuator-04.mp3'), 0, tail_max=0.6, merge=0.4, order='level'), -20)
    export(D6 + '昇降機_サーボ群', window(rec('servo/servo-stair-climber-01.mp3'), 4.0, 8.0, 0.2, 0.8), -20)
    export(D6 + '空圧_排気', cut(rec('pneumatic/pneumatic-rig-air-release-01.mp3'), tail_max=2.5, merge=0.5), -18)
    export(D6 + '空圧ドア_開閉', window(rec('pneumatic/pneumatic-train-door-02.mp3'), 0.0, 16.0, 0.05, 0.6), -20)
    export(D6 + '空圧ドア_シュー', cut(rec('pneumatic/pneumatic-emu-door-hiss-03.mp3'), tail_max=3.0, merge=0.6), -20)
    export(D6 + 'コンプレッサー弁', rec('pneumatic/pneumatic-compressor-valve-04.mp3'), -20)
    export(D6 + '自販機_缶', window(rec('vending/vending-coke-machine-01.mp3'), 0.0, 6.6, 0.01, 0.5), -20)
    export(D6 + '自販機_瓶落下', window(rec('vending/vending-bottle-drop-02.mp3'), 16.8, 5.0, 0.3, 0.8), -20)
    export(D6 + '自販機_うどん', window(rec('vending/vending-udon-japan-03.mp3'), 0.0, 16.0, 0.05, 0.8), -20)
    export(D6 + '蒸気_安全弁', window(rec('steam/steam-safety-valve-02.mp3'), 0.0, 6.9, 0.01, 0.6), -18)
    export(D6 + '蒸気配管_バルブ', window(rec('steam/steam-pipe-valve-beijing-03.mp3'), 6.0, 9.0, 0.3, 0.8), -20)


# ================================================================ 07 ambience loops
def ambience():
    def lp(name, rel, t0=0.0, L=54.0, lufs=-20):
        y, L2 = loop(rec(rel), t0, L)
        export(D7 + name, y, lufs, loop=True, ogg=True, note=f'{L2:.0f}s loop')

    lp('夜の街_LA', 'street_night/street-night-la-01.mp3', 20)
    lp('夜の街_リスボン', 'street_night/street-night-lisbon-03.mp3', 10)
    lp('夜の街_バンクーバー', 'street_night/street-night-vancouver-02.mp3', 20)
    lp('雨の街_小雨', 'rain_city/rain-city-light-street-01.mp3', 0)
    lp('雨の街_強雨', 'rain_city/rain-city-strong-street-02.mp3', 1)
    lp('裏路地_雨樋', 'rain_city/rain-city-backstreet-gutter-03.mp3', 5)
    lp('縦樋の雨', 'rain_city/rain-city-downpipe-04.mp3', 10)
    lp('ネオン看板_うなり', 'neon/neon-sign-buzz-01.mp3', 2, lufs=-22)
    lp('蛍光灯_古い', 'neon/neon-fluorescent-old-02.mp3', 5, lufs=-22)
    lp('蒸気暖房', 'steam/steam-radiator-nyc-01.mp3', 1, L=36)
    lp('配管の蒸気_北京', 'steam/steam-pipe-valve-beijing-03.mp3', 20)
    lp('キーボード_打鍵', 'keyboard/keyboard-whitefox-01.mp3', 10, lufs=-22)
    lp('キーボード_メカ', 'keyboard/keyboard-coolermaster-02.mp3', 2, lufs=-22)
    lp('キーボード_高速', 'keyboard/keyboard-fast-03.mp3', 0.5, L=14, lufs=-22)
    lp('足音ループ_階段', 'footsteps/footsteps-metal-stairs-04.mp3', 4)
    lp('足音ループ_格子床', 'footsteps/footsteps-metal-grate-03.mp3', 0)
    lp('足音ループ_コンクリ', 'footsteps/footsteps-concrete-light-01.mp3', 0, L=27)


JOBS = {'guns': guns, 'guns2': guns2, 'hits': hits, 'electric': electric, 'machines': machines, 'ambience': ambience}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
