"""Version 7: the pack reorganised on the GM's request (2026-11-01).

01_銃 is reduced to six families plus heavy weapons, one file per use:
  ハンドガン（単発） ライフル（単発） アサルトライフル（単発・3連射・フルオート） 機関銃（フルオート）
  ミニガン ロケットランチャー・重火器
05_ハッキング is rebuilt from real recordings of real machines (modem, drives, relays, CRT,
radio, access-control readers, patient monitors, factory alarms) instead of game UI chirps;
see hacking() for what each one is made of. Sources: rec/inbox/CREDITS.md, rec/hack/CREDITS.md.
Everything else (02, 03, 04, 06, 07) keeps the rendered files that pack_v7.py lists.
"""
import numpy as np

from dsp import SR, ns, hp, lp, bp, env_points, make_ir, convolve, Gen, seamless
from master import export
from gen_rec import load
from gen_v3 import seq, gun, kn, lv
from gen_v4 import mo
from gen_v6 import rec, cut, window, env_db, tail_end, segments

D1, D5 = '01_銃/', '05_ハッキング/'


def fl(n):
    return rec(f'firearm_library/{n}.flac')


def chain(takes, gap, gains=None):
    """Bursts placed back to back (gap = seconds from one start to the next)."""
    parts = []
    for i, y in enumerate(takes):
        parts.append((i * gap, y * (gains[i] if gains else 1.0)))
    return seq(parts)


# ================================================================ 01 guns
def guns():
    g = Gen(7101)
    export(D1 + 'ハンドガン_単発', cut(fl('1911-A_42P')), drive=1)
    export(D1 + 'ライフル_単発', cut(fl('tikka-W_29P')), drive=1)
    export(D1 + 'アサルトライフル_単発', cut(fl('ak-47-C_28P')), drive=1)
    # 3-round burst: three near-mic AK singles at 600 rpm (the library's "short burst" take is only two rounds)
    ak = [cut(fl('ak-47-C_28P'), i, tail_max=1.2) for i in range(3)]
    export(D1 + 'アサルトライフル_3連射', chain(ak, 0.1, [1.0, 0.94, 0.9]), drive=1)
    # full auto: the real 10-round burst, then the same burst again a touch quieter -> 20 rounds, 2 s
    fa = cut(fl('ak-47-C_27P'), tail_max=1.5)
    burst_len = segments(fl('ak-47-C_27P'))[0][1] - segments(fl('ak-47-C_27P'))[0][0] + 0.03
    export(D1 + 'アサルトライフル_フルオート', chain([fa, fa], burst_len, [1.0, 0.93]), drive=1)
    # machine gun: PPSh long bursts (900 rpm) three times over, about 3 s of sustained fire
    mg = cut(fl('ppsh-P_34P'), tail_max=1.5)
    bl = segments(fl('ppsh-P_34P'))[0]
    export(D1 + '機関銃_フルオート', chain([mg, mg, mg], bl[1] - bl[0] + 0.02, [1.0, 0.95, 0.9]), drive=1)
    export(D1 + 'ミニガン_掃射', window(rec('minigun/minigun-gatling-close-03.mp3'), 0.0, 7.6, 0.005, 0.4), drive=1)
    # heavy weapons
    export(D1 + 'ロケットランチャー_発射', mo('fpv_missile_launch'), drive=2)
    fire = load('amb/fire_camp.ogg', mono=False)[:ns(6)]
    fire = fire / np.max(np.abs(fire)) * 0.25 * env_points(len(fire), [(0, 0), (0.8, 1), (4, 0.6), (6, 0)])[:, None]
    export(D1 + 'ロケットランチャー_着弾', seq([(0, mo('fpv_expl_big')), (0.04, mo('fpv_expl_grenade_3', 0.6)),
                                            (0.6, lv('bfh1_metal_falling_02', 0.4)), (1.2, lv('bfh1_rock_falling_04', 0.35)),
                                            (0.8, fire)]), drive=2)
    parts, t = [], 0.0
    for i in range(8):
        parts.append((t, mo(['fpv_gun_autocannon_1', 'fpv_gun_autocannon_2'][i % 2], g.u(0.85, 1.0))))
        t += 0.24 + g.u(-0.01, 0.01)
    export(D1 + '重機関砲_掃射', seq(parts), drive=1)
    export(D1 + '榴弾砲_発射', mo('ww2_howitzer_01'), drive=2)


# ================================================================ 05 hacking (real machines, see rec/hack/CREDITS.md)
def hk(n):
    y = load(f'hack/{n}.mp3', mono=False)
    return y / (np.max(np.abs(y)) + 1e-12)


def W(n, t0, dur, fin=0.005, fout=0.08, gain=1.0):
    return window(hk(n), t0, dur, fin, fout) * gain


def room(y, rt60=0.35, mix=0.25, seed=7501):
    """A little room around a dry device sound, so it sits in a space instead of in a vacuum."""
    ir = make_ir(Gen(seed), rt60=rt60, predelay=0.006, lp_start=9000, lp_end=3000, tail_energy=0.35)
    wet = convolve(y, ir)
    out = np.zeros_like(wet)
    out[:len(y)] += y
    return out + wet * mix


def left_only(y):
    return np.repeat(y[:, :1], 2, 1)


def hacking():
    # jack in: a relay slams, a drive spins up and seeks, the modem starts its handshake, a degauss thump, and the hum of the net
    deck = W('hdd-micropolis-spinup-align', 4.5, 2.6, 0.01, 0.5, 0.8)
    hand = bp(W('modem-dialup-hq', 1.2, 1.7, 0.02, 0.3, 0.4), 400, 3500, 2)
    net = W('server-em-emissions', 10.0, 1.6, 0.2, 0.6, 0.35)
    export(D5 + 'ジャックイン', seq([(0, hk('relay-pinball-knocker')), (0.15, deck), (0.7, hand),
                                 (2.3, W('crt-degauss', 0.05, 0.6, 0.002, 0.2, 0.9)), (2.4, net)]), -16)
    # quickhack: a relay click, 0.7 s of modem data, the cutter of a receipt printer as the "sent" mark
    data = bp(W('modem-dial-56k', 9.0, 0.7, 0.005, 0.12, 0.9), 300, 4200, 2)
    export(D5 + 'クイックハック送信', seq([(0, hk('relay-click-short')), (0.08, data),
                                       (0.85, W('printer-thermal-cut', 0.98, 0.5, 0.002, 0.15, 0.7))]), -16)
    # access granted / denied: real card readers and door locks
    export(D5 + 'アクセス許可', room(seq([(0, hk('access-keycard-beep-unlock')), (0.25, hk('access-electronic-lock') * 0.9)])), -17)
    rej = hk('access-card-reject')
    export(D5 + 'アクセス拒否', room(seq([(0, rej), (0.5, rej * 0.95), (1.05, W('access-hotel-deadbolt', 0.38, 0.6, 0.002, 0.1, 0.7))])), -17)
    # ICE: an industrial warning alarm (on-mic channel) over electromagnetic crackle, a big relay closing first
    ice = left_only(W('alarm-industrial-workshop', 0.2, 3.3, 0.01, 0.5))
    export(D5 + 'ICE検知_警告', seq([(0, W('relay-large-stage', 2.0, 0.35, 0.002, 0.1, 0.8)),
                                   (0.05, ice), (0.0, W('server-em-emissions', 65.0, 3.4, 0.05, 0.6, 0.3))]), -15)
    # lockdown: a 90 A contactor, the factory buzzer, then the alarm sequence for 6 s
    export(D5 + '警報_施設ロックダウン', seq([(0, W('relay-contactor-90a', 2.38, 0.5, 0.002, 0.15, 0.9)),
                                        (0.1, W('alarm-factory-buzzer', 0.0, 2.9, 0.005, 0.3, 0.8)),
                                        (0.4, left_only(W('alarm-industrial-workshop', 3.5, 6.0, 0.05, 0.8)))]), -17)
    # glitch: the click of death, chopped radio interference, a bank of solenoids, a failing drive
    g = Gen(7505)
    n = ns(1.0)
    gate = np.ones(n)
    for i in range(14):
        a = int(g.u(0, n - ns(0.05)))
        gate[a:a + int(g.u(ns(0.01), ns(0.05)))] = 0
    inter = W('radio-tuning-interference', 1.3, 1.0, 0.002, 0.05, 0.55) * gate[:, None]
    export(D5 + 'システム異常_グリッチ', seq([(0, W('hdd-wd-click-of-death', 1.7, 1.5, 0.002, 0.2, 0.9)), (0.3, inter),
                                         (1.45, W('relay-solenoid-switches', 2.1, 0.45, 0.002, 0.1, 0.6)),
                                         (1.2, W('hdd-failure-clicking', 0.1, 0.9, 0.005, 0.2, 0.5))]), -15)
    # flatline: the beeps of a real device, then one of them stretched into the steady tone
    beep = W('beeps-stove-buttons', 0.78, 0.22, 0.002, 0.04)
    core = beep[ns(0.04):ns(0.10)]
    tone = seamless(np.concatenate([core] * 80), 4.5, 0.03)
    tone = tone * env_points(len(tone), [(0, 0), (0.01, 1), (4.0, 1), (4.5, 0)])[:, None]
    export(D5 + 'フラットライン', room(seq([(0, beep), (0.85, beep * 0.95), (1.55, beep * 0.9), (2.1, beep * 0.85), (2.7, tone * 0.9)]),
                                   rt60=0.5, mix=0.15), -18)
    # scan: a tuner sweep rising, a drive reading, then the reader's beep
    sweep = bp(W('radio-fm-tuning-sweep', 5.0, 1.6, 0.3, 0.2, 0.5), 700, 6000, 2)
    sweep = sweep * env_points(len(sweep), [(0, 0.2), (1.4, 1), (1.6, 0)])[:, None]
    export(D5 + 'スキャン', room(seq([(0, hk('relay-click-short') * 0.6), (0.0, sweep),
                                   (0.2, W('hdd-compaq-1995-access', 16.4, 1.3, 0.01, 0.2, 0.6)),
                                   (1.75, hk('scanner-delivery-beep') * 0.9)])), -18)
    # electronic lock: the code is keyed in and the door releases (one recording, as it happened)
    export(D5 + '電子ロック解除', W('access-keycard-code-door', 1.3, 5.2, 0.01, 0.6), -20, max_gr=6)
    # the net: a 56k dial and handshake; radio sign-off; deck power up / down; data transfer
    export(D5 + 'ネット接続_ダイヤル', W('modem-dial-56k', 0.0, 9.0, 0.005, 1.0), -18)
    export(D5 + '無線_交信終了', seq([(0, hk('radio-walkie-release')), (0.3, hk('radio-squelch-signoff') * 0.8)]), -18)
    export(D5 + 'デッキ起動', seq([(0, W('crt-tv-switch-on', 0.1, 2.4, 0.002, 0.4)), (0.3, W('hdd-wd-spinup-spindown', 0.0, 3.0, 0.05, 0.6, 0.5)),
                                 (1.2, W('coil-gym-lights-power-up-1', 7.0, 2.0, 0.3, 0.6, 0.4))]), -18)
    export(D5 + 'デッキ電源断', seq([(0, W('crt-tv-on-off', 9.6, 2.0, 0.002, 0.5)), (0.1, W('hdd-wd-spinup-spindown', 9.1, 3.9, 0.01, 0.8, 0.6)),
                                  (0, W('coil-50hz-mains-hum', 0.0, 1.2, 0.01, 1.0, 0.3))]), -18)
    export(D5 + 'データ転送', seq([(0, W('radio-rtty-teletype', 2.0, 3.0, 0.05, 0.3, 0.6)), (0.1, W('hdd-wd-7200-idle', 1.5, 2.8, 0.05, 0.4, 0.5)),
                                 (2.75, W('printer-thermal-cut', 0.98, 0.5, 0.002, 0.15, 0.6))]), -18)
    export(D5 + 'ガイガーカウンター', W('geiger-eberline-hotspot', 3.0, 6.0, 0.05, 0.5), -20)
    export(D5 + '電磁ノイズ_盗聴', W('server-em-emissions', 20.0, 6.0, 0.3, 0.8), -22)


# ================================================================ 02 ricochets (2026-11-01: only the two recorded ricochets of 跳弾1/2)
def ricochets():
    from gen_v3 import pan
    r1, r2 = lv('wf_ric1'), lv('wf_ric2')
    # three ricochets, left / right / centre, each one a little quieter (the round losing energy)
    export('02_被弾・着弾/跳弾_連続', seq([(0.0, pan(r1, -0.5)), (0.55, pan(r2, 0.55) * 0.85), (1.2, pan(r1, 0.0) * 0.7)]),
           -16, max_gr=6)
    # pinned down: far rifle bursts, the rounds smacking the cover (rock breaking) and whining off it (跳弾1/2)
    g = Gen(7213)
    parts, t = [], 0.0
    rock = ['bfh1_rock_breaking_01', 'bfh1_rock_breaking_02', 'bfh1_rock_breaking_03']
    while t < 4.2:
        for k in range(int(g.u(3, 6))):
            parts.append((t, gun(['shot-1', 'shot-2', 'shot-3', 'shot-4'][k % 4], 0.22)))
            land = t + 0.08
            r = g.u()
            if r < 0.45:
                parts.append((land, pan(lv(rock[g.r.integers(3)], g.u(0.35, 0.6)), g.u(-0.8, 0.8))))
            elif r < 0.8:
                parts.append((land, pan([r1, r2][g.r.integers(2)] * g.u(0.45, 0.7), g.u(-0.8, 0.8))))
            t += 60 / 750 + g.u(-0.006, 0.006)
        t += g.u(0.4, 0.9)
    export('02_被弾・着弾/制圧射撃を受ける', seq(parts), -15, max_gr=6)


JOBS = {'guns': guns, 'hacking': hacking, 'ricochets': ricochets}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
