"""Version 9 (2026-11-14): no synthesised sounds left where a recording can do it, and the
situations a cyberpunk table keeps running into.

Part A  rebuild the sounds the Nov 3 workstream synthesised (gen_future.py) from real
        recordings: relays, radio squelch, transformer hum, a CRT degauss, hard drives,
        a real ECG monitor, cable plugs, struck metal and glass.
Part B  new situations: blunt weapons, stabbing, a body falling, a scuffle, drawing a gun,
        doors, knocking, lockpicking, searching a room, pills, a time bomb, vent crawling,
        running and wet footsteps, collapsing rubble ...
Part C  new ambience loops: apartment, sewer, rooftop wind, a fire, an elevated highway,
        a construction site, the patient monitor.
Run after gen_v8.py. All raw recordings are CC0 (see rec/*/CREDITS*, rec/lav3/SOURCE.md).
"""
import numpy as np

from dsp import SR, Gen, ns, lp, hp, bp, seamless
from master import export
from gen_rec import load
from gen_v3 import S, gun, kn, lv, D1, D2, D3, D4, D5, D6, D7
from gen_v5 import raw, shot_list, window, soft
from gen_v8 import lv2, chime, spark, room, first_hit, zing
from segs import onsets, cut
import fx
from fx import rate, varispeed, paulstretch, grains, sweep_bp, chorus, seq, pan, env, rms_norm

D10, D11 = '10_端末・通知/', '11_職業別/'


def H(n, gain=1.0):
    return S(f'hack/{n}.mp3', gain)


def RO(n, gain=1.0):
    return S(f'roles/{n}.mp3', gain)


def L3(n, gain=1.0):
    return S(f'lav3/{n}.ogg', gain)


def part(y, t0, t1, fin=0.005, fout=0.05):
    return fx.fade(y[ns(t0):ns(t1)], fin, fout)


def relay():
    """One clean relay click (the first of the recording)."""
    return part(H('relay-click-short'), 0.0, 0.12, 0.001, 0.03)


def clunk():
    """A heavy contactor pulling in."""
    y = H('relay-contactor-90a')
    t = onsets(y)[0]
    return part(y, max(0, t - 0.01), t + 0.5, 0.002, 0.15)


def squelch_open():
    return part(H('radio-walkie-release'), 0.0, 0.15, 0.002, 0.04)


def squelch_close():
    return part(H('radio-squelch-signoff'), 0.0, 0.45, 0.002, 0.1)


def glass(r=1.0, gain=1.0):
    y = first_hit(lv2('chime_GlassGlasses1'), 0.5)
    return fx.fade(rate(y, r), 0.002, 0.1) * gain


def tones(rs, gap=0.11, gain=0.5, src='chime_SilverwareTing2', dur=1.0):
    return seq([(i * gap, chime(r, src, gain, dur)) for i, r in enumerate(rs)])


def power_up(dur=1.8):
    """Real light-fixture power-up hum, sped up a little."""
    y = H('coil-gym-lights-power-up-1')
    return env(rate(y[ns(0.0):ns(dur * 1.3)], 1.3)[:ns(dur)], [(0, 0), (0.3, 0.6), (dur, 1)])


def power_down(dur=1.6):
    hum = fx.tile(H('coil-transformer-basement'), 3.0) * 0.6 + fx.tile(H('hdd-wd-7200-idle'), 3.0) * 0.5
    return varispeed(hum, lambda t: np.clip(1 - t / dur, 0, 1) ** 1.3)


# ================================================================ Part A: 05 hacking
def hack_rebuild():
    g = Gen(9501)
    # deck boot: a contactor pulls in, the fixture hums up, a drive spins, three rising tones
    spin = rate(H('hdd-wd-spinup-spindown')[ns(0.5):ns(3.0)], 1.2)
    y = seq([(0, clunk()), (0.05, power_up(1.8) * 0.6), (0.1, env(spin, [(0, 0), (0.3, 1), (2.0, 0)]) * 0.35),
             (1.85, tones([0.42, 0.5, 0.63], 0.1, 0.4))])
    export(D5 + 'デッキ起動', room(y, 0.25, 0.5), -17)
    # deck power-down: a click, everything sags to silence, a last relay
    y = seq([(0, relay()), (0.05, power_down(1.6) * 0.6), (1.75, clunk() * 0.6)])
    export(D5 + 'デッキ電源断', room(y, 0.25, 0.5), -18, max_gr=6)
    # jack-out: interference falls away, the net whooshes out backwards, the plug comes out
    rt = fx.tile(H('radio-tuning-interference'), 1.6)
    fall = sweep_bp(rt, 7000, 300, 1.0) * np.linspace(1, 0.1, ns(1.6))[:, None]
    back = paulstretch(lv('woosh_Swish1'), 5.0)[::-1]
    back = env(rate(back, 0.8), [(0, 0), (len(back) / SR * 0.8, 1), (len(back) / SR * 1.25, 0)])
    plug = part(RO('jack-plug'), 0.0, 0.5, 0.001, 0.2)
    y = seq([(0, back * 0.7), (0.2, fall * 0.4), (1.7, plug * 0.8)])
    export(D5 + 'ジャックアウト', room(y, 0.3, 0.6), -17)
    # net connect: a modem handshake cut into fast grains, sped up, settling into one tone
    mo = H('modem-dialup-hq')[ns(8.0):ns(13.0)]
    hs = grains(rate(mo, 1.6), 1.2, g, 0.01, 0.04, repeat=0.3, reverse=0.1)
    hs = sweep_bp(hs, 800, 5000, 1.5) * np.linspace(0.4, 1.0, ns(1.2))[:, None]
    y = seq([(0, relay()), (0.05, hs * 0.5), (1.2, squelch_open() * 0.5), (1.25, chime(0.56, gain=0.45))])
    export(D5 + 'ネット接続', room(y, 0.25, 0.5), -18)
    # data transfer: a busy drive and a stream of fine data grains, ends with a relay
    acc = window(H('hdd-compaq-1995-access'), 3.0)
    dat = hp(grains(rate(mo, 2.0), 3.0, g, 0.008, 0.03, repeat=0.2), 1500)
    y = seq([(0, env(acc, [(0, 0), (0.1, 1), (2.8, 1), (3.0, 0)]) * 0.7), (0, dat * 0.2), (3.0, relay())])
    export(D5 + 'データ転送', room(y, 0.25, 0.5), -19)
    # ICE breach: a CRT degauss 'vwoom', the barrier shattering low, a dive and a sub hit
    dg = part(H('crt-degauss'), 0.8, 2.2, 0.01, 0.4)
    y = seq([(0, dg), (0.15, rate(lv('bfh1_glass_breaking_02'), 0.6) * 0.7), (0.15, rate(lv('wm_metal_slam_01'), 0.5) * 0.6),
             (0.2, lv2('mus_drum_boom', 0.8)), (0.25, rate(lv('woosh_Swish1'), 0.7) * 0.6)])
    export(D5 + 'ICE突破', room(y, 0.35, 0.7), -15)
    # traced: a whistle sweeping the band, heartbeat-like thumps quickening, a contactor slams
    wh = window(H('radio-fm-search-whistle'), 3.6)
    thumps, t, gap = [], 0.3, 0.6
    while t < 3.4:
        thumps.append((t, lp(lv2('mus_drum_boom', 0.5), 300)))
        t += gap
        gap = max(0.22, gap * 0.85)
    y = seq([(0, env(wh, [(0, 0), (0.3, 1), (3.6, 1)]) * 0.5)] + thumps + [(3.6, clunk())])
    export(D5 + '逆探知される', room(y, 0.3, 0.6), -16)
    # password crack: a crossbar exchange clicking through combinations, then the lock gives
    cb = window(H('relay-crossbar-timing'), 2.4)
    y = seq([(0, env(cb, [(0, 0), (0.1, 1), (2.3, 1), (2.4, 0)]) * 0.7), (0.3, lv2('kb_KeyCombo3', 0.3)),
             (2.45, lv('wm_lock_open_01', 0.8)), (2.5, chime(0.6, gain=0.45))])
    export(D5 + 'パスワード解読', room(y, 0.25, 0.5), -17)
    # virus injection: interference and modem chatter slowed and stuttering, something wet, a low hit
    vi = grains(rate(fx.seq([(0, rt), (0, mo[:ns(2.0)] * 0.5)]), 0.7), 2.0, g, 0.02, 0.09, repeat=0.5, reverse=0.2)
    y = seq([(0, vi * 0.6), (0.3, rate(lv('wet_slime_09'), 0.5) * 0.3), (1.9, lv2('mus_drum_boom', 0.7)),
             (1.9, part(lv2('fuzz_BigCrackle'), 1.0, 1.6) * 0.4)])
    export(D5 + 'ウイルス注入', room(y, 0.3, 0.6), -16)
    # flatline: the real ECG monitor recording - the last beats, then the flat tone
    ekg = H('ekg-monitor-flatline')
    on = onsets(ekg)
    t_flat = on[-1]
    y = part(ekg, t_flat - 4.9, t_flat + 5.0, 0.3, 1.2)
    bed = rms_norm(fx.tile(RO('hospital-lamps'), len(y) / SR), 0.03)
    export(D5 + 'フラットライン', seq([(0, room(y * 0.5, 0.35, 0.45)[:len(y)]), (0, bed)]), -19)
    # cyberware hits 2 and 3 without the spark layer
    y = seq([(0, lv('bfh1_metal_hit_05', 0.8)), (0.002, lv('wm_metal_sheet_06')), (0.003, lv('knife_BigKnifeTap3', 0.4)),
             (0.003, kn('impactPunch_heavy_001', 0.4))])
    export(D2 + '被弾_サイバーウェア2', y, -15, max_gr=6)
    y = seq([(0, S('more/fpv_metal_clank.mp3')), (0.003, lv('mi_metal_interaction2', 0.5)),
             (0.004, kn('impactPunch_heavy_004', 0.35))])
    export(D2 + '被弾_サイバーウェア3', y, -15, max_gr=6)


# ================================================================ Part A: 10 terminal / notices
def terminal_rebuild():
    g = Gen(9601)
    # holophone ring: a two-note glass motif three times, with the buzz of a phone's radio between
    buzz = fx.fade(window(S('lav/em_CellReception1.ogg'), 0.35), 0.005, 0.05) * 0.25
    ring = seq([(0, chime(0.5, gain=0.55, dur=0.6)), (0.14, chime(0.63, gain=0.55, dur=0.7))])
    y = seq([(k * 0.9, ring) for k in range(3)] + [(0.45 + k * 0.9, buzz) for k in range(3)])
    export(D10 + 'ホロフォン_着信', room(y, 0.3, 0.5), -18)
    export(D10 + 'ホロコール_接続', room(seq([(0, squelch_open() * 0.6), (0.06, tones([0.5, 0.63], 0.09, 0.45))]), 0.3, 0.5), -18)
    export(D10 + 'ホロコール_切断', room(seq([(0, squelch_close() * 0.6), (0.02, tones([0.63, 0.5], 0.09, 0.4))]), 0.3, 0.5), -19)
    export(D10 + 'メッセージ受信', room(seq([(0, relay() * 0.3), (0.01, glass(0.95, 0.7))]), 0.3, 0.5), -19)
    cash = part(RO('cash-counter'), 0.0, 0.5, 0.005, 0.15)
    export(D10 + '送金完了', room(seq([(0, cash * 0.5), (0.35, tones([0.56, 0.75], 0.1, 0.45))]), 0.3, 0.5), -18)
    export(D10 + '残高不足', room(seq([(0, lv2('chime_GoodThunk3', 0.5)),
                                    (0.03, lp(tones([0.4, 0.33], 0.16, 0.5, dur=0.9), 2200))]), 0.3, 0.5), -19)
    sw = hp(fx.fade(rate(lv('woosh_Swish6'), 1.8), 0.002, 0.05), 900)
    export(D10 + 'AR_ウィンドウ表示', room(seq([(0, sw * 0.5), (0.08, glass(1.15, 0.35))]), 0.25, 0.4), -20)
    export(D10 + 'AR_ウィンドウ閉じる', room(seq([(0, sw[::-1] * 0.5), (0.06, glass(0.9, 0.25))]), 0.25, 0.4), -21)
    tick = fx.fade(rate(lv('knife_BigKnifeTap3'), 1.3)[:ns(0.18)], 0.001, 0.08)
    export(D10 + 'AR_マーカー', room(tick * 0.6, 0.25, 0.4), -21)
    zoom = rate(fx.fade(window(raw('servo/servo-sg90-close-02.mp3'), 0.35), 0.01, 0.08), 1.4)
    export(D10 + '視覚_ズーム', room(seq([(0, zoom * 0.5), (len(zoom) / SR, relay() * 0.5)]), 0.2, 0.4), -20)
    em2 = fx.tile(S('lav/em_ComputerMonitor2.ogg'), 3.0)
    beam = np.concatenate([sweep_bp(em2[:ns(1.5)], 400, 3000, 0.7), sweep_bp(em2[ns(1.5):], 3000, 400, 0.7)])
    beam = env(beam, [(0, 0), (0.3, 1), (2.7, 1), (3.0, 0)])
    export(D10 + '生体スキャン', room(seq([(0, beam * 0.6), (3.05, chime(0.63, gain=0.45))]), 0.3, 0.5), -19)
    y = seq([(0, clunk() * 0.8), (0.05, power_up(1.2) * 0.5), (1.2, tones([0.42, 0.5, 0.63], 0.1, 0.4))])
    export(D10 + '義体OS_起動', room(y, 0.25, 0.5), -18)
    cer = lambda r: fx.fade(rate(first_hit(lv2('chime_CeramicBowl1'), 0.35), r), 0.002, 0.1)
    export(D10 + '警告_注意', room(seq([(0, relay() * 0.4), (0.02, lp(cer(0.5), 3000) * 0.6), (0.2, lp(cer(0.5), 3000) * 0.6)]),
                                 0.3, 0.5), -18)
    st = L3('mus_stab_fade')
    export(D10 + 'ニュース速報', bp(env(st[:ns(2.6)], [(0, 1), (2.0, 1), (2.6, 0)]), 200, 9000), -18)
    export(D10 + 'ナビ_案内開始', room(seq([(0, sw * 0.3), (0.05, glass(0.85, 0.5)), (0.17, glass(1.12, 0.45))]), 0.3, 0.5), -19)


# ================================================================ Part A: 11 role gadgets
def roles_rebuild():
    g = Gen(9701)
    sv = lambda d: fx.fade(window(raw('servo/servo-sg90-close-02.mp3'), d), 0.01, 0.06)
    # solo: smartlink lock
    y = seq([(0, sv(0.3) * 0.35)] + [(0.25 + i * 0.12, chime(0.85 + 0.15 * i, gain=0.35, dur=0.25)) for i in range(3)] +
            [(0.62, chime(0.6, gain=0.35, dur=0.5)), (0.62, relay() * 0.4)])
    export(D11 + 'ソロ_照準ロック', room(y, 0.25, 0.4), -18)
    # optical camo: a shimmer of stretched glass rising, the air bending around you
    sh = hp(paulstretch(glass(1.0), 12.0, win=0.15), 1800)[:ns(1.6)]
    sh = chorus(env(sh, [(0, 0), (1.2, 1), (1.6, 0)]), 0.004, 1.5, 0.5)
    ws = rate(lv('woosh_Swish3'), 1.3)
    y = seq([(0, sh * 0.5), (0.9, ws * 0.4), (0.0, env(power_up(1.5), [(0, 0), (1.5, 0.3)]) * 0.3)])
    export(D11 + 'ソロ_光学迷彩_起動', room(y, 0.3, 0.5), -18)
    export(D11 + 'ソロ_光学迷彩_解除', room(y[::-1], 0.3, 0.5), -18)
    # reflex booster: the world drops away (reverse rush, sub), time stretches, then snaps back
    rush = rate(lv('woosh_Swish1')[::-1], 0.5)
    pad = env(paulstretch(lv2('mus_pad_whine'), 3.0)[:ns(2.2)], [(0, 0), (0.4, 1), (2.0, 1), (2.2, 0)])
    beat = lp(lv2('mus_drum_boom', 0.6), 250)
    y = seq([(0, rush * 0.6), (len(rush) / SR, lv2('mus_drum_boom', 0.9)), (len(rush) / SR, pad * 0.35),
             (len(rush) / SR + 0.6, beat), (len(rush) / SR + 1.5, beat), (len(rush) / SR + 2.2, rate(lv('woosh_Swish2'), 1.2) * 0.6)])
    export(D11 + 'ソロ_加速装置', room(y, 0.3, 0.6), -16)
    # medtech: defibrillator - capacitor whine, the thump through the body
    T = 0.9
    whine = varispeed(lv2('saw_Wobble02'), lambda t: 0.6 * (4.0 ** np.clip(t / T, 0, 1)))[:ns(T)]
    whine = env(whine, [(0, 0), (T * 0.8, 0.6), (T, 0)])
    y = seq([(0, whine * 0.5), (T, kn('impactPunch_heavy_003')), (T, lp(lv2('mus_drum_boom', 0.7), 400)),
             (T + 0.02, L3('rpg_cloth2', 0.4))])
    export(D11 + 'メドテック_除細動器', room(y, 0.3, 0.5), -16)
    air = part(raw('pneumatic/pneumatic-rig-air-release-01.mp3'), 0.2, 0.75, 0.002, 0.2)
    export(D11 + 'メドテック_エアハイポ', room(seq([(0, relay() * 0.5), (0.02, air * 0.7)]), 0.2, 0.4), -18)
    export(D11 + 'メディア_録画開始', room(seq([(0, relay() * 0.5), (0.05, tones([0.6, 0.75], 0.08, 0.35, dur=0.6))]), 0.2, 0.4), -20)
    export(D11 + 'メディア_録画停止', room(seq([(0, relay() * 0.5), (0.05, tones([0.75, 0.6], 0.08, 0.35, dur=0.6))]), 0.2, 0.4), -20)
    # lawman: stun baton - swing, arc, crack
    y = seq([(0, lv('woosh_Swish2', 0.5)), (0.18, spark(0.6, 0.6, 'spark/spark-jacobs-ladder-03.mp3')),
             (0.2, spark(0.2, 0.9, 'spark/spark-130kv-short-02.mp3')), (0.2, kn('impactPunch_medium_002', 0.5))])
    export(D11 + 'ローマン_スタン警棒', room(y, 0.25, 0.5), -16)
    export(D11 + 'ローマン_ボディカメラ', room(seq([(0, relay() * 0.5), (0.04, sv(0.15) * 0.3), (0.2, chime(0.7, gain=0.35, dur=0.6))]),
                                          0.2, 0.4), -20)
    # exec: sign and stamp, approved
    y = seq([(0, L3('paper_PenWriting1')[:ns(1.2)] * 0.6), (1.25, lv2('chime_GoodThunk3', 0.7)), (1.3, kn('impactPlate_light_000', 0.3)),
             (1.45, tones([0.5, 0.63], 0.1, 0.4))])
    export(D11 + 'エグゼク_契約承認', room(y, 0.3, 0.5), -18)
    office = rms_norm(fx.tile(RO('office-quiet'), 2.5), 0.03)
    y = seq([(0, squelch_open() * 0.4), (0.05, tones([0.42, 0.5, 0.56], 0.12, 0.35)), (0.3, env(office, [(0, 0), (0.5, 1), (2.5, 0)]))])
    export(D11 + 'エグゼク_ホロ会議', room(y, 0.3, 0.5), -19)
    # fixer: encrypted line - tuning through interference until it locks
    tun = sweep_bp(window(H('radio-tuning-interference'), 1.6), 600, 4000, 1.2)
    y = seq([(0, env(tun, [(0, 0), (0.2, 1), (1.5, 1), (1.6, 0)]) * 0.5), (1.6, squelch_open() * 0.5), (1.62, relay() * 0.5),
             (1.7, chime(0.56, gain=0.4))])
    export(D11 + 'フィクサー_暗号回線', room(y, 0.25, 0.5), -18)


# ================================================================ Part B: new situations
def melee_more():
    g = Gen(9801)
    sw = lambda k: lv(f'woosh_Swish{k}', 0.5)
    export(D4 + '鈍器_殴打', seq([(0, sw(1)), (0.2, kn('impactWood_heavy_001')), (0.202, kn('impactPunch_heavy_000', 0.7))]),
           -15, max_gr=6)
    export(D4 + '鉄パイプ_殴打', seq([(0, sw(2)), (0.18, lv('bfh1_metal_hit_04')), (0.182, kn('impactPunch_heavy_003', 0.7))]),
           -15, max_gr=6)
    export(D4 + 'ナイフ_刺す', seq([(0.0, kn('knifeSlice2')), (0.01, kn('impactPunch_medium_000', 0.6)),
                                     (0.02, lv('wet_slime_05', 0.5))]), -15, max_gr=6)
    fall = seq([(0, L3('rpg_cloth3', 0.5)), (0.12, kn('impactSoft_heavy_002')), (0.14, L3('rpg_dropLeather', 0.6)),
                (0.35, kn('impactSoft_medium_003', 0.4))])
    export(D4 + '人が倒れる', fall, -15, max_gr=6)
    parts, t = [], 0.0
    while t < 3.2:
        r = g.u()
        if r < 0.4:
            parts.append((t, L3(f'rpg_cloth{1 + g.r.integers(4)}', g.u(0.4, 0.8))))
        elif r < 0.7:
            parts.append((t, kn(f'impactPunch_medium_00{g.r.integers(5)}', g.u(0.4, 0.8))))
        else:
            parts.append((t, L3(f'rpg_footstep0{g.r.integers(10)}', g.u(0.5, 0.9))))
        t += g.u(0.12, 0.35)
    export(D4 + '格闘_もみ合い', seq(parts), -16, max_gr=6)


def gun_handling():
    export(D1 + '銃を抜く', seq([(0, L3('rpg_cloth1', 0.5)), (0.08, L3('rpg_beltHandle1', 0.7)), (0.25, kn('metalClick', 0.6))]), -19, max_gr=6)
    rp = gun('reloadPistol')
    export(D1 + 'スライドを引く', cut(rp, 1.15, len(rp) / SR, pre=0.01, fade=0.15), -19, max_gr=6)


def foley_more():
    g = Gen(9901)
    export(D6 + 'ドア_開ける', L3('rpg_doorOpen_1'), -19)
    export(D6 + 'ドア_閉める', L3('rpg_doorClose_2'), -18, max_gr=6)
    export(D6 + 'ドア_きしむ', L3('rpg_creak1'), -19)
    export(D6 + '金属扉_閉まる', seq([(0, lv('wm_metal_close_01')), (0.02, lv('wm_metal_slam_01', 0.5))]), -16, max_gr=6)
    knock = seq([(0, kn('impactWood_medium_001')), (0.22, kn('impactWood_medium_003', 0.9)), (0.44, kn('impactWood_medium_002', 0.95))])
    export(D6 + 'ノック', knock, -17, max_gr=6)
    bang = seq([(i * g.u(0.18, 0.26), kn(f'impactWood_heavy_00{i % 5}', g.u(0.8, 1.0))) for i in range(6)])
    export(D6 + 'ドアを激しく叩く', bang, -15, max_gr=6)
    clicks = [(i * g.u(0.25, 0.5), L3('drawer_FlashlightClicky1', g.u(0.2, 0.35))[:ns(0.12)]) for i in range(6)]
    clicks += [(i * 0.6 + 0.2, kn('metalClick', 0.25)) for i in range(3)]
    export(D6 + '鍵開け_ピッキング', seq(clicks + [(2.8, L3('s100_key_open_01'))]), -20, max_gr=6)
    y = seq([(0, L3('drawer_DrawerMove', 0.7)), (0.9, L3('drawer_Rummage2', 0.6)[:ns(2.0)]), (3.0, L3('paper_RifflePages1', 0.5)),
             (4.2, L3('drawer_CloseDrawer1', 0.8))])
    export(D6 + '家探し_引き出しを漁る', y, -19)
    export(D6 + '書類をめくる', seq([(0, L3('paper_PageTurn1')), (0.7, L3('paper_PageTurnFast', 0.8))]), -20)
    export(D6 + '錠剤を出す', seq([(0, L3('pill_TwistCap1', 0.7)), (0.6, L3('pill_PrescriptionShake1'))]), -19)
    export(D6 + '缶を開ける', L3('can_PluckTab1'), -19, max_gr=6)
    export(D6 + '小銭_クレジットチップ', L3('rpg_handleCoins'), -19)
    rub = seq([(0, lv('bfh1_rock_falling_03')), (0.2, lv('bfh1_rock_breaking_01', 0.9)), (0.5, lv('bfh1_metal_falling_02', 0.7)),
               (0.8, lv('bfh1_rock_falling_06', 0.8)), (1.3, lv('bfh1_wood_breaking_02', 0.6)), (1.8, lv('bfh1_rock_falling_09', 0.6))])
    export(D6 + '瓦礫の崩落', rub, -15, max_gr=6)
    # time bomb: a relay ticking each second, faster at the end, and a final contactor
    ticks, t, gap = [], 0.0, 1.0
    for i in range(12):
        ticks.append((t, relay() * 0.6))
        t += gap
        if i >= 7:
            gap = max(0.25, gap * 0.7)
    export(D6 + '時限装置_カウントダウン', seq(ticks + [(t, clunk())]), -18, max_gr=6)
    export(D6 + '時限装置_解除', seq([(0, relay() * 0.6), (0.1, lp(tones([0.6, 0.45], 0.14, 0.45), 4000)),
                                          (0.3, part(raw('pneumatic/pneumatic-rig-air-release-01.mp3'), 0.2, 1.0, 0.01, 0.4) * 0.3)]), -19)
    duct = []
    t = 0.0
    while t < 4.0:
        duct.append((t, rate(lv(f'wm_metal_sheet_0{1 + g.r.integers(5)}'), g.u(0.6, 0.8)) * g.u(0.25, 0.45)))
        duct.append((t + 0.05, L3(f'rpg_cloth{1 + g.r.integers(4)}', 0.4)))
        t += g.u(0.45, 0.8)
    export(D6 + 'ダクトを這う', seq(duct), -19, max_gr=6)
    run = []
    t = 0.0
    for i in range(14):
        run.append((t, L3(f'rpg_footstep0{i % 10}', g.u(0.8, 1.0))))
        t += g.u(0.27, 0.31)
    export(D6 + '足音_走る', seq(run), -19, max_gr=6)
    wet = seq([(0, L3('v2_footstep_wet_01')), (0.55, L3('v2_footstep_wet_02')), (1.1, L3('v2_footstep_wet_03')),
               (1.65, L3('v2_footstep_wet_01', 0.9)), (2.2, L3('v2_footstep_wet_02', 0.9)), (2.75, L3('v2_footstep_wet_03', 0.9))])
    export(D6 + '足音_濡れた路面', wet, -20, max_gr=6)
    export(D6 + 'エアロック_開閉', seq([(0, part(raw('pneumatic/pneumatic-emu-door-hiss-03.mp3'), 0.0, 3.0, 0.01, 0.6) * 0.8),
                                       (2.6, lv('wm_metal_slam_01', 0.6))]), -17, max_gr=6)


# ================================================================ Part C: loops
LR, XR = 54.0, 4.0
T = LR + XR


def bed(y, gain=1.0):
    return fx.tile(rms_norm(y, 1.0), T, 1.5) * gain


def loops():
    g = Gen(9950)
    # megabuilding apartment: the fridge, the city through the window, a pipe now and then
    y = bed(L3('home_Refridgerator'), 0.5) + lp(bed(L3('home_Outside'), 0.4), 1500)
    y = seq([(0, y)] + [(t0, pan(L3(f'plop_PlopAiry{1 + i % 3}', 0.05), g.u(-0.6, 0.6))) for i, t0 in enumerate([11, 27, 38, 47])])[:ns(T)]
    export(D7 + 'アパートの部屋', seamless(y, LR, XR), -24, loop=True, ogg=True)
    # sewer: running water, drips, a low ventilation rumble
    y = bed(L3('w40_loop_water_02'), 0.5) + bed(L3('v2_loop_water_01'), 0.35) + lp(bed(L3('home_Dehumidifier'), 0.3), 400)
    drips = [(t0, pan(L3(['plop_PlopAiry1', 'plop_PlopAiry2', 'plop_PlopAiry3', 'plop_PlopViscous1'][g.r.integers(4)], g.u(0.06, 0.15)),
                      g.u(-0.8, 0.8))) for t0 in np.arange(5.0, 50.0, 1.7) + Gen(9951).u(-0.5, 0.5, 27)]
    y = seq([(0, y)] + drips)[:ns(T)]
    export(D7 + '下水道', seamless(y, LR, XR), -23, loop=True, ogg=True)
    # rooftop: wind, the city far below
    y = bed(RO('wind-desert'), 0.6) + lp(bed(S('amb/park_city.ogg'), 0.3), 800)
    export(D7 + '屋上の風', seamless(y[:ns(T)], LR, XR), -23, loop=True, ogg=True)
    # fire: a burning room, slowed down so it sounds bigger, debris giving way now and then
    fire = bed(rate(S('amb/fire_camp.ogg'), 0.8), 0.7) + bed(S('amb/fire_camp.ogg'), 0.4)
    y = seq([(0, fire)] + [(t0, pan(lv(nm, 0.25), g.u(-0.6, 0.6))) for t0, nm in
                           [(9, 'bfh1_wood_breaking_01'), (23, 'bfh1_wood_falling_02'), (36, 'bfh1_wood_breaking_03'), (47, 'bfh1_metal_falling_01')]])[:ns(T)]
    export(D7 + '火災現場', seamless(y, LR, XR), -23, loop=True, ogg=True)
    export(D7 + '高架下の幹線道路', seamless(bed(L3('v2_loop_highway')), LR, XR), -23, loop=True, ogg=True)
    export(D7 + '工事現場', seamless(bed(L3('v2_loop_construction_site')), LR, XR), -24, loop=True, ogg=True)
    # patient monitor: the real ECG beeps, cut on whole beats so the loop keeps the rhythm, in a hospital room
    ekg = H('ekg-monitor-flatline')
    on = [t for t in onsets(ekg) if t < 23.0]
    a, b = on[0] - 0.1, on[-1] - 0.1
    beat = ekg[ns(a):ns(b)]
    Lb = len(beat) / SR
    n_rep = int(np.ceil(54.0 / Lb))
    beats = np.concatenate([beat] * n_rep)
    Lm = len(beats) / SR
    hosp = fx.tile(rms_norm(RO('hospital-corridor'), 1.0), Lm + 4, 2.0) * 0.4
    hosp = seamless(hosp, Lm, 4.0)
    m = min(len(beats), len(hosp))
    hosp = hosp / (np.sqrt(np.mean(hosp ** 2)) + 1e-12) * 0.12
    export(D7 + 'メドテック_生体モニター', beats[:m] * 0.9 + hosp[:m], -27, loop=True, ogg=True)


JOBS = {'hack': hack_rebuild, 'terminal': terminal_rebuild, 'roles': roles_rebuild, 'melee': melee_more,
        'gun': gun_handling, 'foley': foley_more, 'loops': loops}

if __name__ == '__main__':
    import sys
    for k, f in JOBS.items():
        if len(sys.argv) < 2 or k in sys.argv[1:]:
            f()
