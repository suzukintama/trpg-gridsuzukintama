"""Version 3: raw recordings, used as they are.

Rule of thumb: if a real recording of the thing exists, it goes in untouched
(trim, level, fade only). Several recordings are placed in sequence when the
action has several steps (bursts, reloads, a grenade bouncing then exploding).
No synthetic layers and no artificial reverb, except where noted for sounds
that are electronic by nature (heart monitor beep, tinnitus).

Sources: rec/guns (Free Firearm Sound Library), rec/kenney, rec/lav, rec/amb.
"""
import os

import numpy as np

from dsp import SR, Gen, ns, tvec, lp, env_points, osc, seamless
from master import export
from gen_rec import load, norm

D1, D2, D3, D4, D5, D6, D7 = ('01_銃/', '02_被弾・着弾/', '03_爆発/', '04_近接/', '05_ハッキング/',
                              '06_機械・乗り物/', '07_環境音ループ/')


def S(rel, gain=1.0, pitch=1.0):
    """A recording as stereo, peak-normalised, times gain."""
    y = load(rel, mono=False, pitch=pitch)
    return y / (np.max(np.abs(y)) + 1e-12) * gain


def gun(n, gain=1.0):
    return S(f'guns/{n}.wav', gain)


def kn(n, gain=1.0):
    return S(f'kenney/{n}.ogg', gain)


def lv(n, gain=1.0):
    return S(f'lav/{n}.ogg', gain)


def pan(y, p):
    """Constant-power balance of a stereo signal, p in [-1, 1]."""
    a = (p + 1) * np.pi / 4
    return y * np.array([np.cos(a), np.sin(a)]) * np.sqrt(2)


def seq(parts, length=None):
    """parts: [(time_s, stereo_array), ...] -> one stereo array."""
    end = max(ns(t) + len(a) for t, a in parts)
    out = np.zeros((max(end, ns(length or 0)), 2))
    for t, a in parts:
        i = ns(t)
        out[i:i + len(a)] += a
    return out


# ================================================================ 01 guns
def guns():
    g = Gen(3101)
    export(D1 + '拳銃_単発', gun('pistol-1'), drive=1)
    export(D1 + '拳銃_3連射', seq([(0, gun('pistol-1')), (0.19, gun('pistol-2', 0.95)), (0.33, gun('pistol-3', 0.92))]), drive=1)
    # heavy single shot: hammer cock then the Mossberg's big single report
    export(D1 + 'ヘビーピストル', seq([(0, kn('metalClick', 0.35)), (0.12, kn('metalLatch', 0.3)),
                                    (0.45, gun('chimney-1'))]), drive=1)

    def burst(takes, rpm, count, jitter=0.004):
        parts, t = [], 0.0
        for i in range(count):
            parts.append((t, gun(takes[i % len(takes)], 1.0 if i == 0 else g.u(0.86, 0.96))))
            t += 60 / rpm + g.u(-jitter, jitter)
        return seq(parts)

    export(D1 + 'SMG_連射', burst(['smg-1', 'smg-2', 'smg-3'], 900, 7), drive=1)
    export(D1 + 'アサルトライフル_3点', burst(['shot-1', 'shot-2', 'shot-3'], 700, 3), drive=1)
    export(D1 + 'アサルトライフル_フルオート', burst(['shot-1', 'shot-2', 'shot-3', 'shot-4'], 650, 14), drive=1)
    # PPSh: the recording itself is a real long burst, sliced; play the slices back to back
    export(D1 + 'サブマシンガン_長連射', seq([(0, gun('rotisserie-1')), (0.26, gun('rotisserie-2')),
                                          (0.52, gun('rotisserie-3'))]), drive=1)
    # the shotgun take carries a synthetic 65 Hz sub added by the project it came from: strip it
    from dsp import hp
    sg = hp(gun('shotgun-1'), 110, 4)
    export(D1 + 'ショットガン+ポンプ', seq([(0, sg / np.max(np.abs(sg))), (0.6, gun('pump', 0.3)),
                                          (1.25, gun('shell-2', 0.3))]), drive=1)
    rl = gun('reload')
    export(D1 + 'スナイパーライフル', seq([(0, gun('marksman-2')), (1.0, rl[ns(0.85):ns(1.3)] * 0.5)]), drive=1)
    export(D1 + 'リロード_拳銃', gun('reloadPistol'), -20)
    export(D1 + 'リロード_ライフル', gun('reload'), -19)
    export(D1 + '弾切れ_カチッ', seq([(0, kn('metalClick', 0.8)), (0.45, kn('metalClick', 0.75))]), -22)
    # smart gun: recorded UI chirps for the lock-on, then real SMG rounds
    lock = [(0.0, lv('ui_select_001', 0.3)), (0.12, lv('ui_select_002', 0.3)), (0.24, lv('ui_select_003', 0.3)),
            (0.38, lv('ui_confirmation_001', 0.35))]
    shots = [(0.62 + i * 0.067, gun(['smg-1', 'smg-2', 'smg-3'][i % 3], 0.95)) for i in range(5)]
    export(D1 + 'スマートガン_ロック射撃', seq(lock + shots), drive=1)
    # tech weapon (fictional): recorded electric hum as the charge, a cannon report, an electric hit
    hum = lv('wf_electrobolt_hum', 0.5)
    hum = hum * env_points(len(hum), [(0, 0), (len(hum) / SR, 1)])[:, None]
    export(D1 + 'レールガン_チャージ射撃', seq([(0, hum), (len(hum) / SR, lv('bang_cannon_02')),
                                              (len(hum) / SR, lv('wf_electrobolt_hit', 0.6))]), drive=1)


# ================================================================ 02 hits
def hits():
    # flesh: a heavy body thump plus a wet tear (punch + slime recordings, nothing synthetic)
    for i, (p, w, s) in enumerate([('impactPunch_heavy_000', 'wet_slime_05', 'wet_splash_03'),
                                   ('impactPunch_heavy_003', 'wet_slime_09', 'wet_splash_07'),
                                   ('impactPunch_heavy_001', 'wet_slime_12', 'wet_splash_11')], 1):
        export(D2 + f'被弾_肉体{i}', seq([(0, kn(p)), (0.004, lv(w, 0.75)), (0.02, lv(s, 0.35))]), -15, max_gr=6)
    export(D2 + '被弾_かすり傷', seq([(0, kn('impactSoft_medium_001', 0.6)), (0.0, lv('wet_slime_02', 0.5))]), -17, max_gr=6)
    export(D2 + '被弾_防弾プレート', seq([(0, kn('impactPlate_heavy_002')), (0.003, kn('impactPunch_heavy_002', 0.5))]),
           -15, max_gr=6)
    # cyberware: a round smacking into metal
    export(D2 + '被弾_サイバーウェア1', seq([(0, kn('impactMetal_heavy_001')), (0.002, lv('bfh1_metal_hit_02', 0.7)),
                                         (0.004, kn('impactPunch_heavy_004', 0.35))]), -15, max_gr=6)
    export(D2 + '被弾_サイバーウェア2', seq([(0, lv('bfh1_metal_hit_05')), (0.002, kn('impactMetal_heavy_003', 0.8)),
                                         (0.004, kn('impactPunch_medium_003', 0.3))]), -15, max_gr=6)
    export(D2 + '着弾_コンクリート', seq([(0, kn('impactMining_001')), (0.01, lv('bfh1_rock_breaking_01', 0.6)),
                                       (0.45, kn('impactMining_003', 0.9)), (0.46, lv('bfh1_rock_falling_02', 0.4))]),
           -16, max_gr=6)
    export(D2 + '着弾_金属', seq([(0, kn('impactMetal_medium_000')), (0.33, lv('bfh1_metal_hit_01', 0.9)),
                                (0.52, kn('impactMetal_medium_003', 0.85))]), -16, max_gr=6)
    export(D2 + 'ガラス破砕', seq([(0, lv('bfh1_glass_breaking_02')), (0.05, lv('bfh1_glass_breaking_05', 0.7)),
                               (0.35, lv('bfh1_glass_falling_01', 0.6))]), -15, max_gr=6)
    export(D2 + '跳弾1', lv('wf_ric1'), -16, max_gr=6)
    export(D2 + '跳弾2', lv('wf_ric2'), -16, max_gr=6)
    # pinned down: far rifle bursts, rounds smacking cover nearby
    g = Gen(3213)
    parts, t = [], 0.0
    impacts = ['impactMining_000', 'impactMining_002', 'impactMetal_light_002', 'impactMining_004']
    while t < 4.2:
        for k in range(int(g.u(3, 6))):
            parts.append((t, gun(['shot-1', 'shot-2', 'shot-3', 'shot-4'][k % 4], 0.22)))
            r = g.u()
            land = t + 0.08
            if r < 0.6:
                parts.append((land, pan(kn(impacts[g.r.integers(4)], g.u(0.5, 0.9)), g.u(-0.8, 0.8))))
            elif r < 0.8:
                parts.append((land, pan(lv(['wf_ric1', 'wf_ric2'][g.r.integers(2)], 0.45), g.u(-0.8, 0.8))))
            t += 60 / 750 + g.u(-0.006, 0.006)
        t += g.u(0.4, 0.9)
    export(D2 + '制圧射撃を受ける', seq(parts), -15, max_gr=6)


# ================================================================ 03 explosions
def explosions():
    pre = [(0, kn('metalClick', 0.3)), (0.25, kn('metalLatch', 0.3)),
           (0.75, lv('wf_gren_strong_bounce1', 0.45)), (1.0, lv('wf_gren_strong_bounce2', 0.3))]
    export(D3 + '手榴弾_投擲から爆発', seq(pre + [(1.6, lv('bang_cannon_01')), (1.6, lv('wf_gren_strong_explosion1', 0.7)),
                                            (1.9, lv('bfh1_rock_falling_04', 0.35))]), drive=2)
    fire = load('amb/fire_camp.ogg', mono=False)[:ns(8)]
    fire = fire / np.max(np.abs(fire)) * 0.35 * env_points(len(fire), [(0, 0), (1.0, 1), (5, 0.7), (8, 0)])[:, None]
    export(D3 + '大爆発_車両', seq([(0, lv('bang_cannon_03')), (0.02, lv('wf_gren_strong_explosion2', 0.8)),
                                 (0.35, lv('bang_cannon_05', 0.6)), (0.7, lv('bfh1_metal_falling_02', 0.5)),
                                 (1.1, lv('bfh1_glass_falling_02', 0.4)), (1.6, lv('bfh1_metal_falling_04', 0.35)),
                                 (1.0, fire)]), drive=2)
    export(D3 + 'EMPグレネード', seq([(0, lv('scifi_forceField_002', 0.5)), (0.6, lv('bang_bang_05')),
                                   (0.6, lv('wf_electrobolt_hit', 0.8)), (0.75, lv('em_CellReception1', 0.4)[:ns(2.5)]
                                                                         * env_points(ns(2.5), [(0, 1), (2.5, 0)])[:, None])]),
           drive=2)
    # flashbang: real bang, then a ringing tone in the ears (tinnitus is a pure tone by nature)
    n = ns(6.0)
    ring = osc(3950, n, 'sine') * 0.12 * env_points(n, [(0, 0), (0.05, 1), (2.5, 0.6), (6, 0)]) ** 1.5
    export(D3 + '閃光弾_耳鳴り', seq([(0, lv('bang_bang_02')), (0.02, np.stack([ring, ring * 0.92], 1))]), drive=1)


# ================================================================ 04 melee
def melee():
    export(D4 + '刀_抜刀', lv('knife_BigKnifeUnsheath1'), -17, max_gr=6)
    export(D4 + '斬撃_空振り', seq([(0, pan(lv('woosh_Swish1'), -0.3)), (0.5, pan(lv('woosh_Swish3', 0.9), 0.3))]), -17)
    export(D4 + '斬撃_命中', seq([(0, lv('woosh_Slash')), (0.1, lv('wf_blade_hitflsh1', 0.9)),
                               (0.11, lv('wet_slime_07', 0.5))]), -15, max_gr=6)
    export(D4 + 'アームブレード展開', seq([(0, lv('mech_RatchetHarsh1', 0.5)), (0.3, lv('mech_SpringLoadedBlade2')),
                                     (0.34, lv('knife_SmallKnifeUnsheath1', 0.5))]), -15, max_gr=6)
    export(D4 + '打撃_パンチ', seq([(0, lv('woosh_Swish5', 0.4)), (0.12, kn('impactPunch_medium_001')),
                                (0.42, lv('woosh_Swish6', 0.4)), (0.55, kn('impactPunch_heavy_004'))]), -15, max_gr=6)
    export(D4 + '打撃_サイバーアーム', seq([(0, lv('mech_RatchetHarsh2', 0.45)), (0.25, lv('woosh_Swish2', 0.5)),
                                      (0.4, kn('impactPunch_heavy_000')), (0.402, kn('impactPlate_heavy_001', 0.55)),
                                      (0.6, lv('mech_CableCoiler1', 0.3))]), -14, max_gr=6)


# ================================================================ 05 hacking (electronic by nature: recorded UI / computer sounds)
def hacking():
    export(D5 + 'ジャックイン', seq([(0, kn('metalLatch', 0.6)), (0.3, lv('scifi_computerNoise_001', 0.5)[:ns(2.5)]),
                                 (2.6, lv('scifi_forceField_000', 0.8))]), -16)
    gl = [(0.05 * i, lv(f'ui_glitch_00{1 + i % 4}', 0.5)) for i in range(10)]
    export(D5 + 'クイックハック送信', seq(gl + [(0.55, lv('scifi_computerNoise_002', 0.4)[:ns(0.8)]),
                                       (1.3, lv('ui_confirmation_003', 0.6))]), -16)
    export(D5 + 'アクセス許可', lv('ui_confirmation_001'), -17)
    export(D5 + 'アクセス拒否', seq([(0, lv('ui_error_004')), (0.2, lv('ui_error_006'))]), -17)
    a = lv('loop_alarm_02', 0.8)
    export(D5 + 'ICE検知_警告', seq([(i * len(a) / SR, a) for i in range(4)] + [(0.1, lv('ui_glitch_002', 0.5))]), -15)
    a = lv('loop_alarm_01')
    export(D5 + '警報_施設ロックダウン', seq([(i * len(a) / SR, a) for i in range(3)]), -17)
    sc = lv('em_CellReception2')[:ns(2.0)] * env_points(ns(2.0), [(0, 1), (1.5, 0.6), (2.0, 0)])[:, None]
    export(D5 + 'ショート_感電', seq([(0, lv('wf_electrobolt_hit')), (0.02, sc * 0.7), (0.4, lv('wf_electrobolt_hit', 0.6))]), -15)
    g = Gen(3508)
    parts = [(0.07 * i + g.u(0, 0.03), lv(f'ui_glitch_00{1 + g.r.integers(4)}', g.u(0.4, 0.9))) for i in range(25)]
    export(D5 + 'システム異常_グリッチ', seq(parts + [(0, lv('scifi_computerNoise_003', 0.35)[:ns(2.0)])]), -15)
    # heart monitor: the beep itself is a pure tone, so it stays synthesized
    beep = lambda a: np.stack([osc(1000, ns(0.12), 'sine') * env_points(ns(0.12), [(0, 0), (0.004, 1), (0.1, 1), (0.12, 0)]) * a] * 2, 1)
    flat = np.stack([osc(1000, ns(5.0), 'sine') * env_points(ns(5.0), [(0, 0), (0.004, 1), (4.4, 1), (5, 0)])] * 2, 1)
    export(D5 + 'フラットライン', seq([(0, beep(0.35)), (0.85, beep(0.32)), (1.55, beep(0.28)), (2.1, beep(0.25)),
                                   (2.7, flat * 0.35)]), -18)
    export(D5 + 'スキャン', seq([(0, lv('scifi_forceField_003', 0.7)), (0.9, lv('ui_select_004', 0.4)),
                              (1.3, lv('ui_confirmation_002', 0.4))]), -18)
    export(D5 + '電子ロック解除', seq([(0, lv('ui_select_001', 0.4)), (0.16, lv('ui_select_002', 0.4)),
                                   (0.32, lv('ui_select_003', 0.4)), (0.48, lv('ui_select_001', 0.4)),
                                   (0.75, lv('ui_confirmation_001', 0.5)), (0.95, lv('wm_lock_open_01'))]), -18)


# ================================================================ 06 machines
def machines():
    export(D6 + '自動ドア_開', seq([(0, lv('wf_door_start')), (1.5, lv('wf_door_stop', 0.8))]), -18)
    export(D6 + 'エレベーター到着', seq([(0, lv('wf_elevator_move', 0.7)), (2.0, lv('wf_door_stop', 0.6)),
                                    (2.2, lv('ui_bong_001', 0.5)), (2.5, lv('wf_door_start', 0.6))]), -18)


# ================================================================ 07 ambience loops (no gunshots)
LR, XR = 54.0, 4.0
T = LR + XR


def bed(rel, start=0.0, gain=1.0, hi=None):
    """A recording stretched to T seconds by tiling it with crossfades (for short sources)."""
    y = load(rel, mono=False)[ns(start):]
    y = y / (np.sqrt(np.mean(y ** 2)) + 1e-12)
    if len(y) < ns(T):
        X = min(ns(1.0), len(y) // 4)
        out = y.copy()
        while len(out) < ns(T):
            t = np.linspace(0, 1, X)[:, None]
            out = np.concatenate([out[:-X], out[-X:] * np.cos(t * np.pi / 2) + y[:X] * np.sin(t * np.pi / 2), y[X:]])
        y = out
    y = y[:ns(T)]
    if hi:
        y = lp(y, hi, 4)
    return y * gain


def loop_out(y):
    return seamless(y[:ns(T)], LR, XR)


def ambience():
    g = Gen(3701)
    # rain on a neon street: rain + rain on glass, a neon sign's electrical hum, far traffic, one distant thunder
    y = (bed('amb/rain_heavy.ogg', 0, 0.5) + bed('amb/rain_window.ogg', 0, 0.18) +
         bed('lav/em_EMRoomNoise1.ogg', 0, 0.05) + bed('amb/park_city.ogg', 0, 0.25, hi=1200))
    th = load('amb/thunder_distant.ogg', mono=False)
    y[ns(28):ns(28) + len(th)] += th / np.max(np.abs(th)) * 0.5
    export(D7 + '雨のネオン街', loop_out(y), -20, loop=True, ogg=True)
    # back alley: far city, rooftop AC unit, a neon sign's hum, now and then something metal
    y = (bed('amb/park_city.ogg', 0, 0.35, hi=800) + bed('lav/fan_OutdoorACUnit.ogg', 0, 0.3) +
         bed('lav/em_EMRoomNoise2.ogg', 0, 0.05))
    for t0, nm in [(9.0, 'wm_metal_hit_02'), (21.5, 'wm_metal_falling_01'), (37.0, 'wm_metal_hit_04'), (46.0, 'wm_keys_02')]:
        s = lv(nm, 0.12)
        y[ns(t0):ns(t0) + len(s)] += pan(s, g.u(-0.7, 0.7))
    export(D7 + '裏路地', loop_out(y), -22, loop=True, ogg=True)
    # server room: room AC, computer towers, fans
    y = (bed('amb/ac_room.ogg', 0, 0.5) + bed('lav/em_ComputerTower1.ogg', 0, 0.25) +
         bed('lav/fan_ComputerFan.ogg', 0, 0.35) + bed('lav/em_ComputerTower3.ogg', 0, 0.15))
    export(D7 + 'サーバールーム', loop_out(y), -22, loop=True, ogg=True)
    # abandoned factory: big fan, a machine still running, metal knocking somewhere
    y = bed('lav/fan_LargeFan.ogg', 0, 0.4) + bed('lav/loop_machine_05.ogg', 0, 0.12)
    for t0, nm in [(7.0, 'wm_metal_slam_01'), (19.0, 'wm_metal_sheet_02'), (31.0, 'bfh1_metal_falling_03'), (44.0, 'wm_metal_hit_03')]:
        s = lv(nm, 0.15)
        y[ns(t0):ns(t0) + len(s)] += pan(s, g.u(-0.8, 0.8))
    export(D7 + '廃工場', loop_out(y), -22, loop=True, ogg=True)
    # inside a vehicle at night in the rain
    y = bed('amb/bus_ride.ogg', 1.5, 0.6) + bed('amb/rain_heavy.ogg', 0, 0.45, hi=2500)
    export(D7 + '車内_雨の夜', loop_out(y), -21, loop=True, ogg=True)


JOBS = {'guns': guns, 'hits': hits, 'explosions': explosions, 'melee': melee, 'hacking': hacking,
        'machines': machines, 'ambience': ambience}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
