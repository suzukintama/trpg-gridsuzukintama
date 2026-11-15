"""Version 10 (2026-11-15): one sound per file.

The user's rule: separate sounds are not bundled into one file (staged scenes such
as a grenade from throw to blast are the exception). Files that held several
variants are split into numbered files, and the bundled originals are removed.
Run after gen_v9.py.
"""
import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf

from dsp import SR, Gen, ns
from master import export, ROOT
from gen_v3 import S, gun, kn, lv, D1, D2, D4, D6
from gen_v5 import raw, shot_list
from gen_v8 import first_hit, ricochet
from gen_v9 import L3, part
from fx import seq

REMOVE = ['02_被弾・着弾/着弾_金属', '02_被弾・着弾/着弾_コンクリート', '02_被弾・着弾/跳弾_連続',
          '04_近接/斬撃_空振り', '04_近接/打撃_パンチ', '06_機械・乗り物/エアロック_開閉',
          '06_機械・乗り物/空圧ドア_開閉']


def decode(path):
    with tempfile.TemporaryDirectory() as td:
        w = os.path.join(td, 'a.wav')
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ar', str(SR), w], check=True)
        y, _ = sf.read(w, always_2d=True)
    return y


def split():
    # metal misses: three separate hits
    export(D2 + '着弾_金属1', seq([(0, lv('wm_metal_sheet_06')), (0.001, lv('bfh1_metal_hit_05', 0.7))]), -16, max_gr=6)
    export(D2 + '着弾_金属2', first_hit(lv('mi_metal_interaction1')), -16, max_gr=6)
    export(D2 + '着弾_金属3', S('more/fpv_metal_clank.mp3')[:ns(0.5)], -16, max_gr=6)
    # concrete misses: two separate hits
    export(D2 + '着弾_コンクリート1', seq([(0, lv('bfh1_rock_hit_01')), (0.002, lv('bfh1_rock_breaking_03', 0.7))]), -16, max_gr=6)
    export(D2 + '着弾_コンクリート2', seq([(0, lv('bfh1_hit_04')), (0.005, lv('bfh1_rock_falling_05', 0.6))]), -16, max_gr=6)
    # a third ricochet on its own (跳弾1 metal and 跳弾2 concrete stay as they are)
    export(D2 + '跳弾3', ricochet(Gen(10210), 'metal'), -16, max_gr=6)
    # blade swings and punches: one per file
    export(D4 + '斬撃_空振り1', lv('woosh_Swish1'), -17)
    export(D4 + '斬撃_空振り2', lv('woosh_Swish3'), -17)
    export(D4 + '打撃_パンチ1', seq([(0, lv('woosh_Swish5', 0.4)), (0.12, kn('impactPunch_medium_001'))]), -15, max_gr=6)
    export(D4 + '打撃_パンチ2', seq([(0, lv('woosh_Swish6', 0.4)), (0.13, kn('impactPunch_heavy_004'))]), -15, max_gr=6)
    # one dry-fire click
    export(D1 + '弾切れ_カチッ', kn('metalClick', 0.8), -22)
    # suppressed pistol: one shot, and the three-shot take kept as a burst
    p = raw('suppressed/suppressed-p226-02.mp3')
    export(D1 + 'サプレッサー拳銃', part(p, 0.0, 0.74, 0.001, 0.1), -18, max_gr=6)
    export(D1 + 'サプレッサー拳銃_連射', p, -18, max_gr=6)
    # the bolt and the pump on their own
    rl = gun('reload')
    export(D1 + 'ボルト操作', part(rl, 0.85, 1.3, 0.002, 0.1), -19, max_gr=6)
    export(D1 + 'ショットガン_ポンプ', gun('pump'), -19, max_gr=6)
    # papers: one page turn, and a quick riffle
    export(D6 + '書類をめくる', part(L3('paper_PageTurn1'), 0.0, 1.3, 0.005, 0.2), -20, max_gr=6)
    export(D6 + '書類をパラパラめくる', part(L3('paper_PageTurnFast'), 0.0, 3.0, 0.005, 0.4), -20, max_gr=6)
    # airlock: opening and closing apart
    export(D6 + 'エアロック_開く', part(raw('pneumatic/pneumatic-emu-door-hiss-03.mp3'), 0.0, 3.0, 0.01, 0.6), -17, max_gr=6)
    export(D6 + 'エアロック_閉まる', seq([(0, lv('wm_metal_slam_01')), (0.0, part(raw('pneumatic/pneumatic-rig-air-release-01.mp3'),
                                                                                 0.2, 0.9, 0.005, 0.3) * 0.3)]), -17, max_gr=6)
    # the other workstream's pneumatic door: the hiss of it opening, and it closing, cut from its own recording
    d = decode(os.path.join(ROOT, '06_機械・乗り物', '空圧ドア_開閉.mp3'))
    export(D6 + '空圧ドア_開く', part(d, 3.2, 8.0, 0.05, 0.4), -18, max_gr=6)
    export(D6 + '空圧ドア_閉まる', part(d, 11.0, 13.0, 0.02, 0.4), -18, max_gr=6)
    for rel in REMOVE:
        for ext in ('.mp3', '.ogg'):
            f = os.path.join(ROOT, rel + ext)
            if os.path.exists(f):
                os.remove(f)
                print('removed', rel + ext)


if __name__ == '__main__':
    split()
