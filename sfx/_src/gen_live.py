"""A live show for a rockerboy PC (2026-11-02): the fans, never the band.

All of it is built from real crowd recordings (rec/live/, CC0, see rec/live/CREDITS.md). Recordings
with the band audible were left out or cut around, so the players' own music (or the GM's) can sit on top.
  07_環境音ループ/ライブハウス_*  loops for the scene: before the show, during it, a small dive, the encore,
                                 a hall booing, after the show (all wrap seamlessly)
  09_観客の反応/*                one-shots for the moment: the entrance, the solo, the end of a song,
                                 screams, whistles, gasps, an "aww", boos, "Hey! Hey!"
"""
import numpy as np

from dsp import SR, Gen, ns, lp, hp, make_ir, convolve
from master import export, lufs
from gen_rec import load
from gen_bar import env_db, events_of, stereo_of, pan

D7, D9 = '07_環境音ループ/ライブハウス_', '09_観客の反応/'


def rec(rel, pitch=1.0):
    y = stereo_of(load(f'live/{rel}', mono=False, pitch=pitch))
    return y / (np.max(np.abs(y)) + 1e-12)


def cut(y, t0, t1, fin=0.08, fout=0.6):
    x = y[ns(t0):ns(t1)].copy()
    a, b = min(ns(fin), len(x) // 2), min(ns(fout), len(x) // 2)
    x[:a] *= np.linspace(0, 1, a)[:, None]
    x[-b:] *= np.cos(np.linspace(0, np.pi / 2, b))[:, None] ** 2
    return x


def at(x, db):
    return x * 10 ** ((db - lufs(x)) / 20)


def wrap_add(buf, x, t, gain=1.0):
    """Add x into the circular buffer buf at time t; whatever runs past the end lands on the start."""
    n = len(buf)
    i = ns(t) % n
    x = stereo_of(x) * gain
    k = 0
    while k < len(x):
        m = min(len(x) - k, n - i)
        buf[i:i + m] += x[k:k + m]
        k += m
        i = 0


def bed(parts, L, X=4.0):
    """parts: [(file, t0, t1)] joined with equal-power crossfades, repeated until L s, then closed into a loop."""
    X = ns(X)
    N = ns(L)
    segs = [rec(f)[ns(a):ns(b) if b else None] for f, a, b in parts]
    t = np.linspace(0, 1, X)[:, None]
    out = segs[0]
    k = 1
    while len(out) < N + X:
        p = segs[k % len(segs)]
        out = np.concatenate([out[:-X], out[-X:] * np.cos(t * np.pi / 2) + p[:X] * np.sin(t * np.pi / 2), p[X:]])
        k += 1
    loop = out[:N].copy()
    loop[:X] = out[:X] * np.sin(t * np.pi / 2) + out[N:N + X] * np.cos(t * np.pi / 2)
    return loop / (np.max(np.abs(loop)) + 1e-12)


def scatter(g, L, pool, count, gain_db=(-6, 0), pan_w=0.8):
    """Drop `count` events from pool at random times across a loop of L s (wrapped)."""
    buf = np.zeros((ns(L), 2))
    for i in range(count):
        x = pool[int(g.u(0, len(pool)))]
        wrap_add(buf, pan(x, g.u(-pan_w, pan_w)), (i + g.u(0.1, 0.9)) * L / count, 10 ** (g.u(*gain_db) / 20))
    return buf


def room(x, g, rt60, wet):
    ir = make_ir(g, rt60=rt60, predelay=0.01, lp_start=8000, lp_end=2500, tail_energy=0.5)
    w = convolve(x, ir)[:len(x)]
    return x + w / (np.max(np.abs(w)) + 1e-12) * np.max(np.abs(x)) * wet


def chunks(g, y, n, lo=1.2, hi=2.8):
    """n random windows of a continuous recording (screams and whistles are never isolated in them)."""
    out = []
    for _ in range(n):
        d = g.u(lo, hi)
        t0 = g.u(0.3, len(y) / SR - d - 0.3)
        out.append(cut(y, t0, t0 + d, fin=0.15, fout=0.6))
    return out


def pools():
    g = Gen(9100)
    p = {}
    p['whistle'] = (chunks(g, rec('whistle-cheer-no-clap-1.mp3')[ns(1):], 8)
                    + chunks(g, rec('whistle-cheer-no-clap-2.mp3')[ns(1):], 8))
    p['scream'] = (chunks(g, rec('scream-teen-girls.mp3'), 8)
                   + chunks(g, rec('scream-girls.mp3'), 4))
    p['whoop'] = (events_of(rec('gig-small-calling-for-more.mp3'), min_len=0.2, max_len=2, merge=0.1, rel_thr=10)
                  + events_of(rec('cheer-small-expression.mp3'), min_len=0.2, max_len=3))
    for k, v in p.items():
        print(f'  pool {k}: {len(v)} events')
    return p


# ================================================================ loops
def loops(p):
    g = Gen(9101)
    L = 60.0
    # before the show: a busy hall, a quieter room under it, the odd whoop from someone impatient
    a = bed([('preshow-hall-walla.mp3', 0, None)], L)
    b = bed([('preshow-hubbub.mp3', 0, None)], L)
    w = scatter(g, L, p['whoop'] + p['whistle'], 7, (-14, -6))
    x = at(a, -24) + at(b, -28) + at(w, -31)
    export(D7 + '開演前のざわめき', x, -24, loop=True, ogg=True, note='60s loop: a full hall waiting for the band')

    # during the show: a wall of cheering (no band), with screams and whistles poking out of it
    a = bed([('roar-rock-crowd-large.mp3', 0, None)], L)
    b = bed([('roar-applause-hall.mp3', 2, None)], L)
    c = bed([('roar-rock-crowd.mp3', 0, None), ('roar-club-concorde.mp3', 3.0, 15.0)], L)
    d = bed([('roar-whistles-30000.mp3', 3, 56)], L)
    s = scatter(g, L, p['scream'], 12, (-8, 0)) + scatter(g, L, p['whistle'], 14, (-8, 0))
    x = at(a, -22) + at(b, -27) + at(c, -26) + at(d, -29) + at(s, -27)
    export(D7 + '演奏中の歓声', x, -24, loop=True, ogg=True, note='60s loop: the crowd going for it all through a song, no band')

    # a small dive: maybe sixty people, close, whistling and yelling, in a low concrete room
    a = bed([('gig-small-calling-for-more.mp3', 1, None)], L)
    b = bed([('cheer-whistling-medium-ext.mp3', 0, 20)], L)
    x = at(a, -22) + at(lp(b, 5000), -30)
    x = room(x, g, 0.7, 0.25)
    export(D7 + '小さなハコの熱気', x, -24, loop=True, ogg=True, note='60s loop: a small dive gig, close and rowdy')

    # the encore: rhythmic clapping and cheering, a crowd chanting for more
    a = bed([('encore-applause-rhythmic.mp3', 0, None)], L)
    b = bed([('encore-large-ext-chant.mp3', 0, 50)], L)
    c = bed([('encore-rhythmic-claps-cheers.mp3', 9, None)], L)
    x = at(a, -22) + at(b, -26) + at(c, -30)
    export(D7 + 'アンコールの手拍子', x, -24, loop=True, ogg=True, note='60s loop: clapping in time and calling for one more')

    # a hall that has turned on the band
    L2 = 40.0
    a = bed([('boo-hiss-loop-1.mp3', 0, None), ('boo-hiss-loop-2.mp3', 0, None)], L2, X=2.0)
    b = bed([('boo-long.mp3', 0, 19)], L2, X=2.0)
    x = at(a, -24) + at(b, -27)
    export(D7 + 'ブーイングが続く', x, -24, loop=True, ogg=True, note='40s loop: booing and hissing that does not stop')

    # after the show: the crowd still there, finishing drinks, talking it over
    a = bed([('postshow-rock-venue.mp3', 4, None)], 90.0)
    export(D7 + '終演後のざわめき', a, -25, loop=True, ogg=True, note='90s loop: a rock venue after the last song')


# ================================================================ one-shots
def shots(p):
    g = Gen(9102)

    def out(name, x, note):
        x = x / (np.max(np.abs(x)) + 1e-12)
        export(D9 + name, x, -18, note=note)

    # the entrance: the lights go down and the place explodes, then holds
    r = rec('cheer-stadium-reactions.mp3')
    a = cut(r, 0.0, 6.0, fout=1.5)
    b = cut(rec('roar-rock-crowd-large.mp3'), 10, 22, fin=0.6, fout=4)
    x = np.zeros((ns(13), 2))
    wrap_add(x, a, 0.0)
    wrap_add(x, b * 0.7, 0.4)
    for i in range(5):
        wrap_add(x, pan(p['scream'][int(g.u(0, len(p['scream'])))], g.u(-0.7, 0.7)), 0.5 + i * 1.3, 0.35)
    out('登場の大歓声', x, 'the band walks on: a roar that swells and holds')

    # the solo: a cheer that rises out of the crowd and peaks
    a = cut(rec('cheer-bursts.mp3'), 17.0, 26.5, fin=0.6, fout=1.5)
    a = np.concatenate([a, np.zeros((ns(1.0), 2))])
    for i in range(4):
        # the whistles stay inside the cheer (each event is at most 3 s; the last starts at 6.7 s)
        wrap_add(a, pan(p['whistle'][int(g.u(0, len(p['whistle'])))], g.u(-0.8, 0.8)), 2.5 + i * 1.4, 0.3)
    out('ソロへの歓声', a, 'a cheer rising for a guitar solo')

    # the end of a song: applause and cheering that trails off
    x = cut(rec('cheer-applause-trailing-off.mp3'), 0.5, 17.3, fin=0.05, fout=1.0)
    out('曲終わりの拍手と歓声', x, 'the last chord: applause and cheering, then it settles')

    # a bigger end-of-song: the hall roars and stays loud
    x = cut(rec('roar-club-concorde.mp3'), 2.8, 21.0, fin=0.05, fout=2.0)
    out('曲終わりの大歓声', x, 'the last chord in a packed club: a roar that slowly dies')

    # screams from the front rows
    x = cut(rec('scream-teen-girls.mp3'), 0, 7, fout=1.0)
    y = cut(rec('cheer-women-girls.mp3'), 0.2, 7.5, fout=1.0)
    out('黄色い悲鳴', x + y[:len(x)] * 0.6, 'the front rows screaming for the guitarist')

    # whistles and yells, no clapping
    x = cut(rec('whistle-cheer-no-clap-1.mp3'), 0.8, 14.5, fout=1.0)
    out('口笛と掛け声', x, 'whistling and yelling, no clapping')

    # a small crowd cheering: a few dozen people
    x = cut(rec('cheer-small-audience.mp3'), 0, 4.6, fout=0.6)
    out('まばらな歓声', x, 'a few people cheering: an early slot, a half-empty room')

    # an ooh: a stage dive, a smashed guitar, something nobody expected
    r = rec('ooh-ahh-excitement.mp3')
    ev = events_of(r, min_len=1.0, max_len=5.0, merge=0.3)
    x = max(ev, key=lambda e: np.max(np.abs(e)) * min(len(e), ns(4)))
    out('どよめき', x, 'an "ooh": something on stage nobody saw coming')

    # gasps
    x = cut(rec('gasp-small-crowd.mp3'), 5.0, 9.0, fout=1.0)
    out('息をのむ', x, 'the crowd gasps')

    # an "aww": a string snaps, the set is cut short
    x = cut(rec('aww-1.mp3'), 0, 2.0, fin=0.01, fout=0.4)
    y = cut(rec('aww-2.mp3'), 0, 1.2, fin=0.01, fout=0.3)
    z = np.zeros((ns(2.3), 2))
    wrap_add(z, x, 0)
    wrap_add(z, pan(y, 0.4), 0.1, 0.6)
    out('がっかりの声', z, 'an "aww": a string snaps, the set is cut short')

    # boos
    x = cut(rec('boo-crowd.mp3'), 0.6, 7.2, fout=1.2)
    out('ブーイング', x, 'a crowd booing')
    x = cut(rec('boo-cursing.mp3'), 0, 9.5, fout=1.5)
    out('ブーイング_罵声まじり', x, 'booing, with someone cursing')

    # "Hey! Hey! Hey! Hey!": one recorded shout, a crowd of it, in time with the drums (140 bpm)
    hey = cut(rec('hey-men-shout.mp3'), 0, 0.6, fin=0.003, fout=0.15)
    beat = 60 / 140
    x = np.zeros((ns(beat * 8 + 1.5), 2))
    for i in range(8):
        if i % 2:
            continue
        for v in range(6):
            h = rec('hey-men-shout.mp3', pitch=g.u(0.9, 1.08))
            h = cut(h, 0, min(0.6, len(h) / SR), fin=0.003, fout=0.15)
            wrap_add(x, pan(h, g.u(-0.8, 0.8)), i * beat + g.u(0, 0.035), g.u(0.5, 0.9))
        wrap_add(x, hey, i * beat)
    x = room(x, g, 1.2, 0.35)
    out('ヘイの掛け声', x, '"Hey! Hey! Hey! Hey!" in time, from the whole floor')


if __name__ == '__main__':
    pl = pools()
    loops(pl)
    shots(pl)
