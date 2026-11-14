"""Role sounds (2026-11-03): what each Cyberpunk role needs at the table, cut from real recordings.

All of it comes from rec/roles/ (CC0, see rec/roles/CREDITS.md); the synthesised role gadgets (smartlink lock, optical
camo, sandevistan, defibrillator, ...) are in gen_future.py.
  11_職業別/<role>_*          one-shots: tech tools, medtech saw and stapler, media shutters, lawman cuffs / door kick /
                              radio, fixer cash / case / lighter, nomad engines, skids, crash, bikes, doors, rockerboy feedback
  07_環境音ループ/<role>_*     loops: workshop, clinic, high-rise office, police radio, wasteland wind, campfire, press conference
  python gen_roles.py [shots|loops]
"""
import sys

import numpy as np

from dsp import SR, Gen, ns, lp, hp, make_ir, convolve, seamless
from master import export
from gen_rec import load
from gen_bar import stereo_of

D11, D7 = '11_職業別/', '07_環境音ループ/'


def r(slug, sub='roles'):
    y = stereo_of(load(f'{sub}/{slug}.mp3', mono=False))
    return y / (np.max(np.abs(y)) + 1e-12)


def cut(y, t0, t1, fin=0.01, fout=0.15):
    x = y[ns(t0):ns(t1)].copy()
    a, b = min(ns(fin), len(x) // 2), min(ns(fout), len(x) // 2)
    x[:a] *= np.linspace(0, 1, a)[:, None]
    x[-b:] *= np.cos(np.linspace(0, np.pi / 2, b))[:, None] ** 2
    return x


def cat(*parts, gap=0.0):
    """Join cuts end to end with `gap` seconds of silence between them."""
    out = []
    for p in parts:
        out += [p, np.zeros((ns(gap), 2))]
    return np.concatenate(out[:-1])


_IR = {}


def room(x, rt=0.5, wet=0.15, seed=11):
    if rt not in _IR:
        _IR[rt] = make_ir(Gen(seed), rt60=rt, predelay=0.008, lp_start=9000, lp_end=3000, tail_energy=0.5)
    w = convolve(x, _IR[rt]) * wet
    w[:len(x)] += x
    return w


def at_rms(x, db):
    return x * 10 ** ((db - 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)) / 20)


def loopify(y, L, X=3.0):
    return seamless(y[:ns(L + X)], L, X)


# ================================================================ 11 one-shots
def shots():
    # tech
    export(D11 + 'テック_溶接', cut(r('weld-continuous'), 10.0, 16.0, 0.05, 0.4), drive=8)
    export(D11 + 'テック_電動ドリル', cut(r('drill-wood'), 7.6, 12.6, 0.02, 0.3), -16)
    export(D11 + 'テック_インパクト', cut(r('impact-wrench'), 1.9, 4.1, 0.005, 0.15), -16)
    export(D11 + 'テック_グラインダー', cut(r('grinder-metal'), 4.4, 10.5, 0.02, 0.5), -16)
    export(D11 + 'テック_ハンマー', cut(r('hammer-metal'), 8.6, 13.3, 0.005, 0.3), -16)
    export(D11 + 'テック_工具箱を漁る', cut(r('toolbox-rummage'), 1.7, 7.0, 0.02, 0.3), -16)
    export(D11 + 'テック_工具を落とす', cut(r('wrench-drop'), 0.0, 1.4, 0.002, 0.2), -16)
    # medtech
    export(D11 + 'メドテック_骨ノコ', cut(r('bonesaw'), 10.8, 15.5, 0.05, 0.4), -16)
    export(D11 + 'メドテック_ステープラー', cut(r('stapler-plier'), 1.8, 4.5, 0.005, 0.2), -16)
    # media
    export(D11 + 'メディア_シャッター', cut(r('shutter-1'), 0.9, 1.7, 0.002, 0.1), drive=7)
    export(D11 + 'メディア_連写', cut(r('shutter-burst'), 0.0, 1.3, 0.002, 0.1), drive=4)
    # lawman
    export(D11 + 'ローマン_手錠', cut(r('cuffs-lock'), 5.2, 7.3, 0.005, 0.2), drive=7)
    export(D11 + 'ローマン_ドア蹴破り', room(cut(r('door-kick-wood'), 0.0, 1.0, 0.002, 0.2), 0.7, 0.2), -14)
    export(D11 + 'ローマン_金属扉を破る', room(cut(r('door-metal-impact'), 0.0, 1.6, 0.002, 0.2), 0.8, 0.2), -14)
    radio = r('radio-police-short')
    export(D11 + 'ローマン_無線', cat(cut(r('radio-beep'), 0.0, 0.8, 0.002, 0.1), cut(radio, 0.0, 3.3, 0.01, 0.1), gap=0.1), -18)
    # fixer
    export(D11 + 'フィクサー_札束カウンター', cut(r('cash-counter'), 0.0, 3.1, 0.005, 0.2), -16)
    export(D11 + 'フィクサー_札を数える', cut(r('cash-hand'), 1.6, 6.6, 0.02, 0.3), -17)
    latch = r('case-latch')
    export(D11 + 'フィクサー_ケースを開ける', cat(cut(latch, 2.0, 2.6, 0.002, 0.1), cut(latch, 6.0, 6.7, 0.002, 0.15), gap=0.15), drive=7)
    export(D11 + 'フィクサー_ライター', cut(r('zippo'), 4.9, 8.5, 0.005, 0.2), -17)
    # nomad
    export(D11 + 'ノーマッド_エンジン始動', cut(r('car-start'), 0.0, 6.5, 0.005, 0.8), -16)
    export(D11 + 'ノーマッド_空ぶかし', cut(r('v8-rev'), 0.0, 3.7, 0.005, 0.4), -15)
    export(D11 + 'ノーマッド_急ブレーキ', cut(r('tire-squeal'), 2.2, 7.0, 0.05, 0.6), -15)
    export(D11 + 'ノーマッド_衝突事故', cut(r('crash-ext'), 2.0, 7.5, 0.002, 0.6), -14)
    export(D11 + 'ノーマッド_バイク通過', cut(r('moto-flyby'), 4.5, 11.0, 0.3, 0.8), -15)
    export(D11 + 'ノーマッド_バイク始動', cut(r('moto-start-zx6r'), 0.5, 8.0, 0.005, 0.8), -16)
    export(D11 + 'ノーマッド_車のドア', cut(r('cardoor-open-close'), 2.7, 6.0, 0.005, 0.2), -16)
    # rockerboy
    export(D11 + 'ロッカー_ハウリング', cut(r('feedback-guitar'), 15.4, 21.0, 0.1, 0.8), -16)
    export(D11 + 'ロッカー_ギターの悲鳴', cut(r('feedback-scream'), 0.0, 1.8, 0.005, 0.3), -16)
    export(D11 + 'ロッカー_シールドを挿す', cut(r('jack-plug'), 0.0, 2.0, 0.002, 0.3), -17)


# ================================================================ 07 loops
def loops():
    L = 54.0
    # tech: a quiet workshop with a machine shop working further off
    y = at_rms(r('workshop-quiet')[ns(30):ns(30 + L + 3)], -26) + at_rms(r('workshop-metal')[:ns(L + 3)], -30)
    export(D7 + 'テック_工房', loopify(y, L), -22, loop=True, ogg=True)

    # medtech: a long hospital corridor and the hum of its lamps
    y = at_rms(r('hospital-corridor')[ns(10):ns(70)], -26)[:ns(L + 3)]
    # something bangs in the corridor at 32.2 s, 12 dB over the rest: pull it down so it doesn't jump out
    y[ns(31.9):ns(33.1)] *= np.interp(np.arange(ns(1.2)), [0, ns(0.25), ns(0.95), ns(1.2)], [1, 0.3, 0.3, 1])[:, None]
    y = y + at_rms(r('hospital-lamps')[:ns(42)], -36)[np.arange(ns(L + 3)) % ns(42)]
    export(D7 + 'メドテック_診療所', loopify(y, L), -24, loop=True, ogg=True)

    # exec: an office floor, quiet keyboards and air handling
    y = r('office-quiet')[ns(10):ns(10 + L + 3)]
    export(D7 + 'エグゼク_高層オフィス', loopify(y, L), -24, loop=True, ogg=True)

    # lawman: police radio traffic, transmissions separated by breathing room under a low hiss
    g = Gen(6100)
    parts = [cut(r('radio-police'), 0.2, 23.8, 0.02, 0.1), cut(r('radio-chatter'), 1.0, 8.3, 0.02, 0.1),
             cut(r('radio-police-short'), 0.0, 3.3, 0.01, 0.1)]
    beep = cut(r('radio-beep'), 0.0, 0.8, 0.002, 0.1)
    seq = []
    for p in parts:
        seq += [beep * 0.5, np.zeros((ns(0.1), 2)), p, np.zeros((ns(g.u(2.5, 4.5)), 2))]
    y = np.concatenate(seq)
    n = len(y)
    hiss = hp(lp(g.r.standard_normal((n + ns(3), 2)), 5000), 400)
    y = np.concatenate([y, y[:ns(3)]]) + at_rms(hiss, -50)
    export(D7 + 'ローマン_警察無線', seamless(y, n / SR, 3.0), -24, loop=True, ogg=True)

    # nomad: open wasteland wind
    export(D7 + 'ノーマッド_荒野の風', loopify(r('wind-desert-2'), 56.0), -24, loop=True, ogg=True)

    # nomad: a campfire with a little wind around it
    fire = stereo_of(load('amb/fire_camp.ogg', mono=False))
    wind = r('wind-plain')[:len(fire)]
    y = at_rms(fire, -24) + at_rms(wind, -36)
    export(D7 + 'ノーマッド_焚き火', loopify(y, 32.0), -24, loop=True, ogg=True)

    # media: a press conference, murmur of reporters and bursts of camera shutters
    g = Gen(6200)
    murmur = r('office-bank')[ns(20):ns(20 + L + 3)]
    walla = r('walla-exterior-event', 'live')
    y = at_rms(murmur, -28)
    w = at_rms(walla[:ns(31)], -32)
    y[:len(w)] += w
    y[ns(28):ns(28) + len(w) - ns(2)] += w[ns(2):][:len(y) - ns(28)]
    shots = [r('shutter-1'), r('shutter-contarex'), r('shutter-burst')]
    cams = r('camera-paparazzi', 'live')
    t = 1.0
    while t < L - 2:
        if g.u() < 0.3:
            t0 = g.u(0, 9)
            c = cut(cams, t0, t0 + g.u(1.0, 3.0), 0.01, 0.2)
        else:
            s = shots[int(g.u(0, 3))]
            c = s[np.argmax(np.abs(s).max(1) > 0.3) - ns(0.01):][:ns(0.6)]
        c = c * g.u(0.15, 0.4) * np.array([g.u(0.5, 1), g.u(0.5, 1)])
        e = min(len(y), ns(t) + len(c))
        y[ns(t):e] += c[:e - ns(t)]
        t += g.r.exponential(1.6)
    export(D7 + 'メディア_記者会見', loopify(y, L), -24, loop=True, ogg=True)


if __name__ == '__main__':
    which = sys.argv[1:] or ['shots', 'loops']
    for w in which:
        {'shots': shots, 'loops': loops}[w]()
