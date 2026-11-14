"""Version 8 (this branch's v6 redesign): the future, built from real recordings.

Guns stay as raw recordings (v5). Everything that should sound like the future
(hacking, cyberware, tech weapons, UI, AVs, holo-ads, the netspace) is now
designed from real recordings - struck silverware, a bent Japanese saw, real
sparks, servos, keyboards, electromagnetic interference, produced music - using
speed changes, time-stretching, borrowed resonance and grain edits.
No oscillator beeps, no game-UI blips. Run after gen_v5.py (and after the other generators, so these versions win).
"""
import os

import numpy as np
from scipy import signal

from dsp import SR, Gen, ns, lp, hp, bp, peak, seamless
from master import export
from gen_rec import load
from gen_v3 import S, gun, kn, lv, D1, D2, D3, D4, D5, D6, D7
from gen_v5 import raw, shot_list, window, soft
from segs import onsets, shots, cut
from weapons import street_ir, indoor_ir, hall_ir, space
from gen_hits import close_room
from gen_misc import flyby
import fx
from fx import rate, varispeed, paulstretch, resonate, grains, sweep_bp, chorus, tile, seq, pan, env, norm, rms_norm


def lv2(n, gain=1.0):
    return S(f'lav2/{n}.ogg', gain)


def ib(rel, gain=1.0):
    return raw(rel) * gain


def win(rel, dur, center=None, gain=1.0):
    return window(raw(rel), dur, center) * gain


def room(y, wet=0.35, rt=0.5):
    g = Gen(int(abs(hash(rt)) % 1000) + 7)
    return space(y, indoor_ir(g, rt), wet=wet, width=0)


def chime(r, src='chime_SilverwareTing2', gain=1.0, dur=None):
    """A struck-metal ring, slowed down by r (<1 lowers the pitch and lengthens it)."""
    y = rate(lv2(src), r) * gain
    return fx.fade(y[:ns(dur)] if dur else y, 0.002, 0.15)


def spark(dur=0.25, gain=1.0, src='spark/spark-35kv-sparks-01.mp3', at=None):
    y = window(raw(src), dur, at)
    return fx.fade(y, 0.002, min(0.08, dur / 3)) * gain


# ================================================================ 05 netrunning / UI
def netrunning():
    g = Gen(6501)
    # access granted: a tap on the reader, then two rising struck-metal tones
    y = seq([(0, lv2('kb_Button-Push2', 0.35)), (0.05, chime(0.42, gain=0.8)), (0.16, chime(0.56, gain=0.7))])
    export(D5 + 'アクセス許可', room(y, 0.3, 0.5), -18)
    # access denied: a dull knock, a burst of interference, two falling muted tones
    buzz = fx.fade(window(S('lav/em_CellReception1.ogg'), 0.3), 0.005, 0.05)
    y = seq([(0, lv2('kb_Button-Push3', 0.35)), (0.03, lv2('chime_GoodThunk3', 0.6)),
             (0.05, lp(chime(0.36, gain=0.6, dur=0.9), 2500)), (0.2, lp(chime(0.3, gain=0.6, dur=1.0), 2000)),
             (0.04, buzz * 0.25)])
    export(D5 + 'アクセス拒否', room(y, 0.3, 0.5), -18)
    # electronic lock: four key presses, a confirming tone, the bolt, a little air
    keys = [(i * g.u(0.16, 0.22) + 0.0, lv2(f'kb_Button-Push{1 + i % 4}', g.u(0.35, 0.45))) for i in range(4)]
    y = seq(keys + [(0.85, chime(0.6, gain=0.6)), (1.05, lv('wm_lock_open_01')),
                    (1.12, fx.fade(window(raw('pneumatic/pneumatic-rig-air-release-01.mp3'), 0.7, 0.4), 0.01, 0.3) * 0.35)])
    export(D5 + '電子ロック解除', room(y, 0.35, 0.6), -18)
    # jack-in: plug, servo seats it, interference rises, then a dive into the net
    em = fx.tile(S('lav/em_CellReception1.ogg'), 2.2) * 0.6 + fx.tile(S('lav/em_ComputerMonitor1.ogg'), 2.2) * 0.6
    rise = sweep_bp(em, 300, 7000, 1.0) * np.linspace(0.2, 1.0, ns(2.2))[:, None] ** 1.5
    whine = varispeed(lv2('saw_Wobble03'), lambda t: 0.5 * (4.0 ** np.clip(t / 2.2, 0, 1)))[:ns(2.2)]
    whine = env(whine, [(0, 0), (1.5, 0.25), (2.2, 0.5)])
    dive = rate(paulstretch(lv('woosh_Swish1'), 6.0), 0.6)
    dive = env(dive, [(0, 0), (0.1, 1), (len(dive) / SR, 0)])
    shimmer = paulstretch(lv2('chime_SilverwareTing2'), 20.0, win=0.15)[:ns(3.5)]
    shimmer = env(shimmer, [(0, 0), (0.4, 1), (3.5, 0)])
    y = seq([(0, kn('metalLatch', 0.7)), (0.1, fx.fade(window(raw('servo/servo-sg90-close-02.mp3'), 0.35), 0.01, 0.1) * 0.4),
             (0.5, rise * 0.7), (0.5, whine), (2.65, dive * 0.9), (2.65, lv2('mus_drum_boom', 0.8)),
             (2.75, shimmer * 0.35)])
    g2 = Gen(6502)
    export(D5 + 'ジャックイン', space(y, hall_ir(g2, 2.5), wet=0.45, width=0), -16)
    # quickhack: keys, a stutter of interference, a charge that climbs, then the release
    stut = grains(S('lav/em_ComputerMonitor1.ogg'), 0.6, Gen(6503), 0.02, 0.07, repeat=0.5)
    charge = varispeed(lv2('saw_Flick01'), lambda t: 0.8 * (3.2 ** np.clip(t / 0.55, 0, 1)))[:ns(0.6)]
    charge = env(charge, [(0, 0), (0.5, 1), (0.6, 0)])
    out = fx.fade(rate(lv('woosh_Swish3'), 1.6), 0.002, 0.05)
    y = seq([(0, lv2('kb_KeyCombo1', 0.5)), (0.25, stut * 0.5), (0.3, charge * 0.6),
             (0.85, spark(0.25, 0.8)), (0.85, pan(out * 0.6, 0.5))])
    export(D5 + 'クイックハック送信', room(y, 0.3, 0.6), -16)
    # ICE alarm: a real siren, raised and chopped into pulses, with interference underneath
    sir = window(raw('siren/siren-police-pass-fr-03.mp3'), 3.0)
    sir = bp(rate(sir, 1.3), 500, 4500)
    gate = np.zeros(len(sir))
    for k in range(0, len(sir), ns(0.26)):
        gate[k:k + ns(0.17)] = 1
    gate = np.convolve(gate, np.ones(ns(0.008)) / ns(0.008), mode='same')
    pulses = sir * gate[:, None]
    y = seq([(0, pulses), (0, rms_norm(hp(fx.tile(S('lav/em_CellReception2.ogg'), 2.3), 400, 4), 0.04)),
             (1.9, grains(S('lav/em_ComputerMonitor1.ogg'), 0.4, Gen(6504), 0.02, 0.06) * 0.5)])
    export(D5 + 'ICE検知_警告', space(y, indoor_ir(Gen(6505), 0.9), wet=0.5, width=0), -15)
    # facility lockdown: an air-raid siren in a concrete hall, blast doors slamming, air locks
    ar = rate(S('more/ww2_air_raid_siren_01.mp3'), 1.1)
    door = rate(lv('wm_metal_slam_01'), 0.6)
    hiss = fx.fade(window(raw('pneumatic/pneumatic-emu-door-hiss-03.mp3'), 1.5), 0.02, 0.4)
    y = seq([(0, ar * 0.8), (1.2, door), (1.25, hiss * 0.4), (3.4, door * 0.8), (3.45, hiss * 0.3)])
    export(D5 + '警報_施設ロックダウン', space(y, hall_ir(Gen(6506), 3.0), wet=0.9, width=0), -17)
    # system failure: real electronics cut into grains, then the power sags away
    gl = grains(fx.seq([(0, S('lav/em_ComputerMonitor1.ogg')), (0, S('lav2/fuzz_RecordSkipping1.ogg') * 0.5)]), 1.9,
                Gen(6507), 0.015, 0.09, repeat=0.45, reverse=0.2, gap=0.15)
    sag = varispeed(fx.tile(S('lav/em_ComputerTower1.ogg'), 2.0), lambda t: np.clip(1 - t / 0.9, 0, 1) ** 1.5 + 0.0)
    y = seq([(0, gl * 0.8), (1.8, sag[:ns(1.0)] * 0.7)])
    export(D5 + 'システム異常_グリッチ', room(y, 0.25, 0.5), -15)
    # scan: a servo turns, a band of interference sweeps up and back, a soft tone when done
    em2 = fx.tile(S('lav/em_ComputerMonitor2.ogg'), 2.2)
    beam = np.concatenate([sweep_bp(em2[:ns(1.1)], 600, 6000, 0.7), sweep_bp(em2[ns(1.1):], 6000, 600, 0.7)])
    beam = env(beam, [(0, 0), (0.2, 1), (2.0, 1), (2.2, 0)])
    y = seq([(0, fx.fade(window(raw('servo/servo-sg90-close-02.mp3'), 1.0), 0.02, 0.2) * 0.4), (0.1, beam * 0.7),
             (2.3, chime(0.7, gain=0.45))])
    export(D5 + 'スキャン', room(y, 0.35, 0.6), -18)
    # jamming: real static and phone interference with dropouts
    stat = fx.tile(S('more/fpv_static_loop.mp3'), 4.0) * 0.7 + fx.tile(S('lav/em_CellReception1.ogg'), 4.0) * 0.5
    drop = grains(stat, 4.0, Gen(6508), 0.05, 0.3, repeat=0.15, reverse=0.0, gap=0.2)
    export(D5 + '通信妨害_ノイズ', env(drop, [(0, 0), (0.05, 1), (3.6, 1), (4.0, 0)]), -20)
    # typing: a real keyboard, a fast run
    ty = seq([(0, lv2('kb_Typing1')), (2.05, lv2('kb_TypingSlower', 0.9)), (3.9, lv2('kb_KeyCombo3', 0.8))])
    export(D5 + 'ハッキング_タイピング', room(ty, 0.2, 0.4), -19, max_gr=6)
    # flatline: a patient monitor in a quiet room. The monitor tone is a device tone by nature,
    # so it is played through a small-speaker model into a real room tone.
    n = ns(8.5)
    t = np.arange(n) / SR
    def beep(dur):
        m = ns(dur)
        tt = np.arange(m) / SR
        s = np.sin(2 * np.pi * 960 * tt) + 0.18 * np.sin(2 * np.pi * 1920 * tt) + 0.06 * np.sin(2 * np.pi * 2880 * tt)
        e = np.minimum(1, np.minimum(tt / 0.006, (dur - tt) / 0.01))
        return np.tanh(1.4 * s * e) / np.tanh(1.4)
    mon = np.zeros(n)
    for t0, a in [(0.0, 1), (0.85, 0.95), (1.55, 0.9), (2.1, 0.85)]:
        b = beep(0.11)
        mon[ns(t0):ns(t0) + len(b)] += b * a
    fl = beep(5.0)
    mon[ns(2.75):ns(2.75) + len(fl)] += fl
    mon = bp(mon, 450, 4500, 2)
    bed = rms_norm(fx.tile(S('amb/ac_room.ogg'), 8.5), 0.04)
    y = seq([(0, room(mon * 0.3, 0.5, 0.45)[:n]), (0, bed)])
    export(D5 + 'フラットライン', env(y, [(0, 1), (7.8, 1), (8.5, 0)]), -19)


# ================================================================ tech weapons (01)
def tech_guns():
    # smart gun: servo, three rising pings as targets lock, then a real SMG burst with guided trails
    pings = [(0.25 + i * 0.12, chime(0.85 + 0.15 * i, gain=0.35, dur=0.25)) for i in range(3)]
    burst = shot_list('firearm_library/carl-gustav-m45-G_33P.flac')[0]
    trails = [(0.82 + i * 0.07, pan(fx.fade(rate(lv('woosh_Swish2'), 1.8), 0.002, 0.08) * 0.25, (-1) ** i * 0.7))
              for i in range(4)]
    y = seq([(0, fx.fade(window(raw('servo/servo-sg90-close-02.mp3'), 0.3), 0.01, 0.08) * 0.35)] + pings +
            [(0.62, chime(0.6, gain=0.35, dur=0.4)), (0.62, lv2('kb_Button-Push1', 0.3)), (0.8, burst)] + trails)
    export(D1 + 'スマートガン_ロック射撃', y, drive=1)
    # railgun: a bent saw spun up as the capacitor whine, real arcs, then a heavy shot with a
    # cannon's weight, a high-voltage crack and the barrel ringing; vents afterwards
    T = 1.5
    whine = varispeed(lv2('saw_Wobble03'), lambda t: 0.45 * (6.0 ** np.clip(t / T, 0, 1) ** 1.3))[:ns(T)]
    whine = env(whine, [(0, 0), (0.3, 0.3), (T, 1)])
    arc = env(window(raw('spark/spark-jacobs-ladder-03.mp3'), T), [(0, 0), (T * 0.6, 0.3), (T, 0.8)])
    shot = shot_list('firearm_library/tikka-W_29P.flac')[0]
    ring = window(raw('bullet_metal/bullet-metal-steel-plate-01.mp3'), 2.0, 9.5)
    vent = fx.fade(raw('steam/steam-safety-valve-02.mp3'), 0.05, 0.6)
    y = seq([(0, whine * 0.7), (0, arc * 0.6), (T, shot), (T, lv('bang_cannon_02', 0.8)),
             (T, spark(0.35, 0.9, 'spark/spark-130kv-short-02.mp3')), (T + 0.02, ring * 0.35), (T + 0.9, fx.fade(vent[ns(1.5):ns(3.3)], 0.05, 0.6) * 0.3)])
    export(D1 + 'レールガン_チャージ射撃', y, drive=1)
    # distant firefight: real outdoor takes with their echoes, a few blocks away
    g = Gen(6130)
    pool = (shot_list('firearm_library/ak-47-C_28P.flac') + shot_list('firearm_library/walther-ppq-X_39P.flac') +
            shot_list('firearm_library/ppsh-P_30P.flac') + shot_list('firearm_library/ar-15-D_32P.flac'))
    parts, t = [], 0.2
    while t < 9.0:
        s = pool[g.r.integers(len(pool))]
        parts.append((t, s * g.u(0.3, 0.8)))
        t += g.u(0.4, 1.6)
    y = seq(parts)
    y = lp(y, 1600, 4)
    y = space(y, street_ir(g, 2.5, 4.0), wet=0.8, dry_gain=0.6, width=0)
    export(D1 + '遠くの銃撃戦', y, -22)


# ================================================================ 02 hits: cyber flavour
def cyber_hits():
    sh = shots(raw('bullet_metal/bullet-metal-steel-plate-01.mp3'), gap=0.35, maxlen=4.0)
    plate = sh[0][2][:ns(2.5)]
    export(D2 + '被弾_サイバーウェア1', seq([(0, plate), (0.008, spark(0.22, 0.3))]), -15, max_gr=6)
    glitch = grains(window(raw('servo/servo-sg90-close-02.mp3'), 1.5), 0.5, Gen(6201), 0.02, 0.06, repeat=0.6)
    y = seq([(0, lv('bfh1_metal_hit_05', 0.8)), (0.002, lv('wm_metal_sheet_06')), (0.003, lv('knife_BigKnifeTap3', 0.4)),
             (0.01, spark(0.2, 0.3)), (0.12, glitch * 0.3)])
    export(D2 + '被弾_サイバーウェア2', y, -15, max_gr=6)
    y = seq([(0, S('more/fpv_metal_clank.mp3')), (0.003, lv('mi_metal_interaction2', 0.5)),
             (0.01, spark(0.4, 0.35, 'spark/spark-jacobs-ladder-03.mp3'))])
    export(D2 + '被弾_サイバーウェア3', y, -15, max_gr=6)
    # ricochets: the three real ricochets of one recording, one per file
    ric = S('more/fpv_bullet_ricochet.mp3')
    rics = [seg for _, t0, seg in shots(ric, gap=0.3, maxlen=1.2) if t0 > 0.3]
    for i in range(min(2, len(rics))):
        export(D2 + f'跳弾{i + 1}', rics[i], -16, max_gr=6)
    # pinned down: distant rifle bursts, rounds smacking cover close by
    g = Gen(6213)
    far = shot_list('firearm_library/ak-47-C_34P.flac')
    imp = [window(raw('bullet_metal/bullet-metal-steel-plate-01.mp3'), 0.6, 7.6), kn('impactMining_000'), kn('impactMining_002'),
           kn('impactMining_004'), lv('bfh1_rock_breaking_02')]
    parts, t = [], 0.0
    while t < 4.5:
        s = far[g.r.integers(len(far))]
        parts.append((t, lp(s, 3500) * 0.3))
        for k in range(int(g.u(2, 4))):
            land = t + 0.09 + k * 0.08
            x = imp[g.r.integers(len(imp))] * g.u(0.5, 0.9)
            parts.append((land, pan(x, g.u(-0.8, 0.8))))
        if g.u() < 0.4:
            parts.append((t + 0.15, pan(rics[0] * 0.4, g.u(-0.8, 0.8))))
        t += g.u(0.7, 1.3)
    export(D2 + '制圧射撃を受ける', seq(parts), -15, max_gr=6)


# ================================================================ 03 EMP / flashbang
def emp_flash():
    charge = varispeed(lv2('saw_Wobble02'), lambda t: 0.6 * (3.5 ** np.clip(t / 0.7, 0, 1)))[:ns(0.7)]
    charge = env(charge, [(0, 0), (0.6, 0.6), (0.7, 0)])
    hum = fx.tile(S('lav/em_ComputerTower1.ogg'), 3.0) * 0.6 + fx.tile(S('lav/fan_ComputerFan.ogg'), 3.0) * 0.5 + \
        fx.tile(raw('neon/neon-fluorescent-old-02.mp3'), 3.0) * 0.4
    die = varispeed(hum, lambda t: np.clip(1 - t / 1.8, 0, 1) ** 1.3)
    sparks = grains(window(raw('spark/spark-35kv-sparks-01.mp3'), 3.0), 2.0, Gen(6301), 0.02, 0.1, repeat=0.2, gap=0.5)
    sparks = env(sparks, [(0, 1), (2.0, 0)])
    y = seq([(0, charge * 0.6), (0.7, lv('bang_bang_05')), (0.7, spark(0.4, 0.9, 'spark/spark-130kv-short-02.mp3')),
             (0.7, lv2('mus_drum_boom', 0.9)), (0.75, die * 0.5), (0.8, sparks * 0.5)])
    export(D3 + 'EMPグレネード', space(y, street_ir(Gen(6302), 1.2, 2.5), wet=0.6, width=0), drive=2)
    # flashbang: the bang, then the world goes dull and the ears ring.
    bang = lv('bang_bang_02')
    tail = lp(space(bang, indoor_ir(Gen(6303), 0.9), wet=1.0), 700, 4)
    ring = paulstretch(lv2('chime_SilverwareTing2'), 40.0, win=0.2)
    ring = hp(ring, 2500, 4)
    ring = ring[:ns(6.0)] if len(ring) > ns(6.0) else fx.tile(ring, 6.0)
    ring = env(rms_norm(ring, 0.05), [(0, 0), (0.08, 1), (2.5, 0.6), (6.0, 0)])
    y = seq([(0, bang), (0.03, tail * 0.6), (0.02, ring)])
    export(D3 + '閃光弾_耳鳴り', y, drive=1)


# ================================================================ 04 cyber arm
def cyber_arm():
    y = seq([(0, fx.fade(window(raw('servo/servo-motor-03.mp3'), 0.45), 0.02, 0.1) * 0.5),
             (0.2, lv('woosh_Swish2', 0.5)), (0.35, kn('impactPunch_heavy_000')), (0.352, kn('impactPlate_heavy_001', 0.55)),
             (0.55, fx.fade(raw('pneumatic/pneumatic-rig-air-release-01.mp3')[:ns(1.2)], 0.01, 0.4) * 0.35)])
    export(D4 + '打撃_サイバーアーム', room(y, 0.4, 0.5), -14, max_gr=6)


# ================================================================ 06 machines
def machines():
    hum = env(lp(window(raw('servo/servo-stair-climber-01.mp3'), 2.5), 900), [(0, 0), (0.3, 1), (2.0, 1), (2.5, 0)])
    door = fx.fade(raw('pneumatic/pneumatic-emu-door-hiss-03.mp3')[:ns(3.5)], 0.02, 0.6)
    y = seq([(0, hum * 0.5), (2.4, chime(0.45, gain=0.5, dur=1.6)), (2.56, chime(0.38, gain=0.45, dur=1.8)),
             (3.0, door * 0.7)])
    export(D6 + 'エレベーター到着', room(y, 0.4, 0.7), -18)
    # AV: a jet's turbines, a little faster, without the roar's lowest rumble
    jet = window(raw('flyby/flyby-jet-f18-02.mp3'), 14.0)
    av = hp(rate(jet, 1.12), 140, 2)
    export(D6 + 'AV_頭上通過', soft(av, 1.0, 2.5), -16)
    export(D6 + 'ネオン_点灯', soft(lp(raw('neon/neon-flicker-on-04.mp3'), 7000, 4), 0.05, 1.0), -20, max_gr=6)


# ================================================================ 07 loops
LR, XR = 54.0, 4.0
T = LR + XR

ADS = [('af_bella', 'en-us', "Tired of being tired? Ask your clinic about the new reflex upgrade. Results may vary."),
       ('am_adam', 'en-us', "Night markets are open until dawn on level nine. Everything you need. Nothing you don't."),
       ('bf_isabella', 'en-gb', "Your city. Your future. A message from the Metro Development Board."),
       ('am_michael', 'en-us', "Stay hydrated. Stay connected. Stay ahead of the crowd.")]


def holo_ads():
    """Holo-billboard voices: contentless lines, as projected voices (Kokoro TTS, Apache-2.0)."""
    from kokoro_onnx import Kokoro
    from scipy import signal
    kd = os.environ.get('KOKORO_DIR', '/home/user/models/kokoro')
    k = Kokoro(os.path.join(kd, 'kokoro-v1.0.onnx'), os.path.join(kd, 'voices-v1.0.bin'))
    out = []
    for voice, lang, text in ADS:
        s, sr = k.create(text, voice=voice, speed=1.0, lang=lang)
        s = signal.resample_poly(s, SR, sr)
        s = bp(np.stack([s, s], 1), 250, 6000, 3)
        s = chorus(s, 0.003, 0.4, 0.4)
        out.append(norm(s))
    return out


def active_rms(y, target):
    """Scale so the loud (active) part of y has the given RMS."""
    m = np.max(np.abs(y), axis=1)
    act = m > np.max(m) * 0.05
    r = np.sqrt(np.mean(y[act] ** 2)) if act.any() else 1.0
    return y * target / (r + 1e-12)


def voice_level(ad, bed_sig, rel_db):
    """Scale a voice so its speech band sits rel_db relative to the bed's speech band."""
    m = np.max(np.abs(ad), axis=1)
    act = m > np.max(m) * 0.05
    va = np.sqrt(np.mean(bp(ad, 400, 3000)[act] ** 2))
    vb = np.sqrt(np.mean(bp(bed_sig, 400, 3000) ** 2))
    return ad * vb * 10 ** (rel_db / 20) / (va + 1e-12)


def far_av(g):
    jet = window(raw('flyby/flyby-jet-f18-01.mp3'), 12.0)
    return env(lp(rate(jet, 1.1), 2200), [(0, 0), (2, 1), (10, 1), (12, 0)])


def bed(rel, start=0.0, gain=1.0, notch=()):
    y = raw(rel)[ns(start):]
    for f0 in notch:   # remove a steady electronic tone that is in the recording
        b, a = signal.iirnotch(f0, 25, SR)
        y = signal.filtfilt(b, a, y, axis=0)
    y = rms_norm(y, 1.0)
    return fx.tile(y, T, 1.5) * gain


def holo(ad, g, size, lpf):
    return lp(space(ad, street_ir(g, size, 2.0), wet=1.0, dry_gain=0.5, width=0), lpf)


def city_loops():
    g = Gen(6701)
    ads = holo_ads()
    # night street: real street (its constant electronic tone notched out), EV passes,
    # holo-ad voices from up the block, an AV overhead
    base = bed('street_night/street-night-vancouver-02.mp3', 30, 0.8, notch=(2566, 1711, 5132)) + \
        bed('neon/neon-fluorescent-old-02.mp3', 0, 0.04)
    ev = rms_norm(raw('ev_car/ev-car-pass-02.mp3'), 0.25)
    y = seq([(0, base), (12.0, pan(ev, -0.5)), (33.0, pan(ev, 0.5)),
             (6.0, pan(voice_level(holo(ads[0], g, 1.4, 3500), base, -1), 0.4)),
             (21.0, pan(voice_level(holo(ads[1], g, 1.6, 3200), base, -3), -0.5)),
             (40.0, pan(voice_level(holo(ads[3], g, 1.4, 3500), base, -2), 0.3)),
             (26.0, active_rms(far_av(g), 0.8 * 10 ** (-12 / 20)))])[:ns(T)]
    export(D7 + '夜の繁華街', seamless(y, LR, XR), -20, loop=True, ogg=True)
    # rain on a neon street: + one muffled ad through the rain, a distant AV
    base = (bed('rain_city/rain-city-strong-street-02.mp3', 0, 0.55) + bed('rain_city/rain-city-backstreet-gutter-03.mp3', 20, 0.2) +
            lp(bed('neon/neon-sign-buzz-01.mp3', 0, 0.05), 2500))
    th = S('amb/thunder_distant.ogg') * 0.35
    y = seq([(0, base), (28.0, th), (9.0, pan(voice_level(holo(ads[2], g, 1.8, 2200), base, -4), -0.3)),
             (40.0, active_rms(far_av(g), 0.6 * 10 ** (-14 / 20)))])[:ns(T)]
    export(D7 + '雨のネオン街', seamless(y, LR, XR), -20, loop=True, ogg=True)
    # back alley: + a far holo-ad leaking down the alley, an AV high above
    base = (bed('street_night/street-night-lisbon-03.mp3', 10, 0.7) + bed('neon/neon-fluorescent-old-02.mp3', 10, 0.08) +
            bed('steam/steam-pipe-valve-beijing-03.mp3', 0, 0.12))
    y = seq([(0, base), (15.0, pan(voice_level(holo(ads[1], g, 2.5, 1800), base, -5), 0.6)),
             (33.0, active_rms(far_av(g), 0.7 * 10 ** (-14 / 20)))])[:ns(T)]
    export(D7 + '裏路地', seamless(y, LR, XR), -22, loop=True, ogg=True)
    # inside a car at night in the rain: road rumble (high whine of the recording cut), rain on the roof
    y = lp(bed('../amb/bus_ride.ogg', 1.5, 0.6), 2800, 4) + lp(bed('../amb/rain_heavy.ogg', 0, 0.45), 2500, 4)
    export(D7 + '車内_雨の夜', seamless(y, LR, XR), -21, loop=True, ogg=True)


def netspace():
    """Netspace: produced pads smeared out in time, a struck-metal shimmer, faint data whispers."""
    g = Gen(6706)
    TT = 64.0
    padA = fx.tile(paulstretch(lv2('mus_pad_lush_loop'), 6.0, win=0.4), TT, 3.0)
    padB = fx.tile(paulstretch(lv2('mus_pad_ancient_signal'), 10.0, win=0.4, seed=2), TT, 3.0)
    shim = fx.tile(hp(paulstretch(lv2('chime_SilverwareTing2'), 30.0, win=0.25, seed=3), 1500), TT, 3.0)
    low = fx.tile(lp(paulstretch(lv2('saw_Wobble05'), 8.0, win=0.4, seed=4), 600), TT, 3.0)
    y = rms_norm(padA, 0.1) + rms_norm(padB, 0.07) + rms_norm(shim, 0.012) + rms_norm(low, 0.04)
    # slow breathing between the two pads
    t = np.arange(len(y)) / SR
    y = y * (0.85 + 0.15 * np.sin(2 * np.pi * t / 16.0))[:, None]
    parts = [(0, y)]
    ratios = [0.42, 0.5, 0.56, 0.63, 0.75, 0.84]
    tt = 4.5
    while tt < 58:
        parts.append((tt, pan(chime(ratios[g.r.integers(len(ratios))], gain=g.u(0.04, 0.08)), g.u(-0.8, 0.8))))
        tt += g.u(1.2, 3.5)
    tt = 6.0
    while tt < 56:
        w = sweep_bp(fx.tile(S('lav/em_ComputerMonitor1.ogg'), 2.5), g.u(800, 2000), g.u(3000, 7000), 0.6)
        parts.append((tt, pan(env(w, [(0, 0), (1.2, 1), (2.5, 0)]) * 0.04, g.u(-0.9, 0.9))))
        tt += g.u(6, 11)
    y = seq(parts)[:ns(TT)]
    y = space(y, make_big_ir(g), wet=0.7, width=0)[:ns(TT)]
    export(D7 + '電脳空間', seamless(y, 60.0, 4.0), -20, loop=True, ogg=True)


def make_big_ir(g):
    from dsp import make_ir
    return make_ir(g, rt60=4.0, predelay=0.03, lp_start=9000, lp_end=3000, tail_energy=1.2)


def club():
    """A club through the wall: a produced drum-and-bass loop, the wall eating everything but the low end."""
    g = Gen(6704)
    loop = lv2('mus_loop_thiccstep')
    reps = 6
    music = np.concatenate([loop] * reps)            # exactly periodic: loops by itself
    Lm = len(music) / SR
    wall = lp(music, 220, 4) * 1.6 + bp(music, 1800, 5000) * 0.012
    wall = peak(wall, 70, 1.2, 4)
    amb = (fx.tile(rms_norm(lp(load('amb/cafe_murmur.ogg', mono=False), 600), 1.0), Lm + 4, 1.5) * 0.06 +
           fx.tile(rms_norm(load('amb/ac_room.ogg', mono=False), 1.0), Lm + 4, 1.5) * 0.03)
    amb = seamless(amb, Lm, 4.0)
    m = min(len(wall), len(amb))
    wall = wall[:m]
    y = rms_norm(wall, 0.12) + amb[:m]
    y = space(y, indoor_ir(g, 0.6), wet=0.4, width=0)
    # fold the reverb tail back onto the start so the loop stays seamless
    head = y[:len(wall)].copy()
    tail = y[len(wall):]
    head[:len(tail)] += tail
    export(D7 + 'クラブ_壁越し', head, -19, loop=True, ogg=True)


def factory():
    g = Gen(6707)
    y = fx.tile(rms_norm(S('lav/fan_LargeFan.ogg'), 1.0), T, 1.5) * 0.4
    mach = fx.tile(rms_norm(lp(raw('servo/servo-stair-climber-01.mp3'), 2500), 1.0), T, 2.0) * 0.12
    parts = [(0, y + mach)]
    for t0, nm in [(7.0, 'wm_metal_slam_01'), (19.0, 'wm_metal_sheet_02'), (31.0, 'bfh1_metal_falling_03'), (44.0, 'wm_metal_hit_03')]:
        parts.append((t0, pan(rate(lv(nm), 0.8) * 0.15, g.u(-0.8, 0.8))))
    for t0 in [12.0, 37.0]:
        parts.append((t0, pan(raw('pneumatic/pneumatic-compressor-valve-04.mp3') * 0.08, g.u(-0.6, 0.6))))
    y = seq(parts)[:ns(T)]
    y = space(y, hall_ir(g, 3.5), wet=1.0, width=0)[:ns(T)]
    export(D7 + '廃工場', seamless(y, LR, XR), -22, loop=True, ogg=True)


JOBS = {'net': netrunning, 'tech': tech_guns, 'cyber': cyber_hits, 'emp': emp_flash, 'arm': cyber_arm,
        'machines': machines, 'city': city_loops, 'netspace': netspace, 'club': club, 'factory': factory}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
