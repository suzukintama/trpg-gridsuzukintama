"""Version 4: more raw material (rec/more: FpvWebGame + jupixels WW2, all CC0 Freesound/OGA),
metal that actually rings, and the pistol set (single / burst / 15 / endless loop).
Runs on top of gen_v3.py (same file names are overwritten).
"""
import numpy as np

from dsp import SR, Gen, ns, tvec, env_points, seamless, fade
from master import export
from gen_rec import load
from gen_v3 import S, gun, kn, lv, pan, seq, D1, D2, D3, D5, D6, D7
from gen_misc import flyby


def mo(n, gain=1.0):
    return S(f'more/{n}.mp3', gain)


PISTOL = ['pistol-1', 'pistol-2', 'pistol-3']


def first_hit(y, sec=0.3):
    """Keep only the first strike of a recording that has several."""
    y = y[:ns(sec)].copy()
    k = ns(0.04)
    y[-k:] *= np.cos(np.linspace(0, np.pi / 2, k))[:, None] ** 2
    return y


def pistol_shot(g, i):
    return gun(PISTOL[i % 3], 1.0 if i == 0 else g.u(0.88, 0.97))


# ================================================================ pistols
def pistols():
    g = Gen(4101)
    export(D1 + '拳銃_単発', gun('pistol-1'), drive=1)
    export(D1 + '拳銃_3点バースト', seq([(i * 0.085, pistol_shot(g, i)) for i in range(3)]), drive=1)
    # 15 rounds: a steady pace with one short breath in the middle
    parts, t = [], 0.0
    for i in range(15):
        parts.append((t, pistol_shot(g, i)))
        t += g.u(0.16, 0.24) + (0.45 if i == 7 else 0.0)
    export(D1 + '拳銃_15連射', seq(parts), drive=1)
    # endless: groups of shots with pauses, so it keeps a rhythm; starts and ends quiet -> seamless
    groups = [2, 3, 1, 4, 2, 1, 3, 5, 2, 1, 3, 2, 4, 1, 2, 3]
    parts, t = [], 0.1
    k = 0
    for n in groups:
        for j in range(n):
            parts.append((t, pistol_shot(g, k)))
            k += 1
            t += g.u(0.15, 0.22)
        t += g.u(0.45, 1.3)
    L = float(np.ceil(t + 0.6))
    y = seq(parts, length=L)[:ns(L)]
    export(D1 + '拳銃_撃ち続けループ', y, drive=1, loop=True, ogg=True)


# ================================================================ other guns
def guns():
    # real full-auto: three recorded bursts back to back
    export(D1 + 'アサルトライフル_フルオート', seq([(0, mo('fpv_rifle_burst_1')), (0.52, mo('fpv_rifle_burst_2', 0.95)),
                                               (1.04, mo('fpv_rifle_burst_3', 0.95))]), drive=1)
    export(D1 + 'アサルトライフル_バースト実録', mo('fpv_rifle_burst_2'), drive=1)
    rl = gun('reload')
    export(D1 + 'スナイパーライフル', seq([(0, mo('ww2_rifle_shot_01')), (1.2, rl[ns(0.85):ns(1.3)] * 0.45)]), drive=1)
    # turret / vehicle-mounted cannon
    g = Gen(4120)
    parts, t = [], 0.0
    for i in range(8):
        parts.append((t, mo(['fpv_gun_autocannon_1', 'fpv_gun_autocannon_2'][i % 2], g.u(0.85, 1.0))))
        t += 0.24 + g.u(-0.01, 0.01)
    export(D1 + '重機関砲_掃射', seq(parts), drive=1)


# ================================================================ metal hits (ring!)
def metal():
    # cyberware: the bite of the round, then the limb/plating ringing
    export(D2 + '被弾_サイバーウェア1', seq([(0, kn('impactMetal_heavy_001', 0.8)), (0.002, kn('impactPlate_heavy_004')),
                                         (0.004, first_hit(lv('mi_metal_interaction1', 0.7)))]), -15, max_gr=6)
    export(D2 + '被弾_サイバーウェア2', seq([(0, lv('bfh1_metal_hit_05', 0.8)), (0.002, lv('wm_metal_sheet_06')),
                                         (0.003, lv('knife_BigKnifeTap3', 0.45))]), -15, max_gr=6)
    export(D2 + '被弾_サイバーウェア3', seq([(0, mo('fpv_metal_clank')), (0.003, lv('mi_metal_interaction2', 0.55))]),
           -15, max_gr=6)
    # misses on metal: three different rings
    export(D2 + '着弾_金属', seq([(0, kn('impactMetal_heavy_003', 0.7)), (0.002, lv('wm_metal_sheet_06', 0.9)),
                                (0.38, pan(first_hit(lv('mi_metal_interaction1', 0.85)), -0.4)),
                                (0.72, pan(lv('wm_metal_falling_02', 0.8), 0.4))]), -16, max_gr=6)
    export(D2 + '跳弾_連続', mo('fpv_bullet_ricochet'), -16, max_gr=6)


# ================================================================ explosions
def explosions():
    pre = [(0, kn('metalClick', 0.3)), (0.25, kn('metalLatch', 0.3)),
           (0.75, lv('wf_gren_strong_bounce1', 0.45)), (1.0, lv('wf_gren_strong_bounce2', 0.3))]
    export(D3 + '手榴弾_投擲から爆発', seq(pre + [(1.6, mo('fpv_expl_grenade_1')), (1.85, lv('bfh1_rock_falling_04', 0.3))]),
           drive=2)
    fire = load('amb/fire_camp.ogg', mono=False)[:ns(8)]
    fire = fire / np.max(np.abs(fire)) * 0.3 * env_points(len(fire), [(0, 0), (1.0, 1), (5, 0.7), (8, 0)])[:, None]
    export(D3 + '大爆発_車両', seq([(0, mo('fpv_expl_big')), (0.05, mo('fpv_expl_grenade_3', 0.7)),
                                 (0.7, lv('bfh1_metal_falling_02', 0.45)), (1.1, lv('bfh1_glass_falling_02', 0.35)),
                                 (1.6, lv('wm_metal_falling_01', 0.3)), (1.0, fire)]), drive=2)
    export(D3 + 'ミサイル発射', mo('fpv_missile_launch'), drive=2)


# ================================================================ cyberpunk extras
def extras():
    st = mo('fpv_static_loop')
    n = ns(4.0)
    reps = int(np.ceil(n / len(st))) + 1
    y = np.concatenate([st] * reps)[:n] * env_points(n, [(0, 0), (0.05, 1), (3.5, 1), (4.0, 0)])[:, None]
    export(D5 + '通信妨害_ノイズ', y, -20)
    export(D5 + '都市警報サイレン', mo('ww2_air_raid_siren_01'), -18)
    # drone hover loop (12 s) and a pass-by with real doppler
    m = load('more/fpv_quad_motor_loop.mp3', mono=False)
    m = m / np.sqrt(np.mean(m ** 2))
    X = ns(0.5)
    out = m.copy()
    while len(out) < ns(16.5):
        t = np.linspace(0, 1, X)[:, None]
        out = np.concatenate([out[:-X], out[-X:] * np.cos(t * np.pi / 2) + m[:X] * np.sin(t * np.pi / 2), m[X:]])
    export(D6 + 'ドローン_ホバリング', seamless(out[:ns(16.0)], 12.0, 4.0), -20, loop=True, ogg=True)
    src = out[:ns(10.0)].mean(axis=1)
    export(D6 + 'ドローン通過', flyby(src, 10.0, 9.0, 4.0, 5.0, 3.0), -18)


JOBS = {'pistols': pistols, 'guns': guns, 'metal': metal, 'explosions': explosions, 'extras': extras}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
