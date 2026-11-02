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

    # during the show, a full house: a wall of cheering (no band), with screams and whistles poking out of it
    # (the fullest of the four 客入り loops; the other three are in sizes())
    a = bed([('roar-rock-crowd-large.mp3', 0, None)], L)
    b = bed([('roar-applause-hall.mp3', 2, None)], L)
    c = bed([('roar-rock-crowd.mp3', 0, None), ('roar-club-concorde.mp3', 3.0, 15.0)], L)
    d = bed([('roar-whistles-30000.mp3', 3, 56)], L)
    s = scatter(g, L, p['scream'], 12, (-8, 0)) + scatter(g, L, p['whistle'], 14, (-8, 0))
    x = at(a, -22) + at(b, -27) + at(c, -26) + at(d, -29) + at(s, -27)
    export(D7 + '客入り4_満員', x, -24, loop=True, ogg=True, note='60s loop: a full house going for it all through a song, no band')

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

    # applause by the size of the house, for the end of a song
    x = cut(rec('applause-awkward-slow.mp3'), 0.8, 5.6, fin=0.02, fout=0.8)
    out('拍手_ほぼ空', x, 'the end of a song to a nearly empty room: a few slow, uncomfortable claps')
    x = cut(rec('applause-small-group.mp3'), 0, 8.0, fin=0.02, fout=1.0)
    out('拍手_まばら', x, 'the end of a song to twenty or so people')
    x = cut(rec('applause-with-cheering.mp3'), 0, 12.3, fin=0.02, fout=1.5)
    out('拍手_半分', x, 'the end of a song to a half-full room: applause and some cheering')
    a = cut(rec('applause-standing-ovation.mp3'), 0, 12, fin=0.02, fout=3.0)
    b = cut(rec('roar-rock-crowd-large.mp3'), 30, 42, fin=0.3, fout=3.0)
    out('拍手_満席', at(a, -20) + at(b, -24), 'the end of a song to a full house: an ovation')

    # the crowd answering the singer's "Are you ready?": a short, sharp "Yeah!"
    x = np.zeros((ns(3.0), 2))
    wrap_add(x, cut(rec('woo-guys.mp3'), 0, 1.1, fin=0.005, fout=0.3), 0.0)
    wrap_add(x, pan(cut(rec('cheers-yays.mp3'), 0, 2.4, fin=0.005, fout=0.8), -0.3), 0.05, 0.8)
    wrap_add(x, pan(cut(rec('cheer-short.mp3'), 0, 2.8, fin=0.005, fout=0.9), 0.3), 0.08, 0.7)
    out('呼びかけへの返事', x, 'the crowd shouts back "Yeah!" when the singer calls out')

    # the whole floor jumps at once and lands
    x = cut(rec('jump-rhythmic-300.mp3'), 13.1, 15.0, fin=0.01, fout=0.6)
    out('フロアが一斉に跳ぶ', x, 'three hundred people jump on the beat and land together')

    # a scream, then the room breaks into panic: something has gone wrong at the gig
    x = np.zeros((ns(6.5), 2))
    wrap_add(x, cut(rec('panic-scream-single.mp3'), 0, 1.4, fin=0.005, fout=0.3), 0.0)
    wrap_add(x, cut(rec('panic-crowd.mp3'), 0.2, 6.0, fin=0.4, fout=1.5), 0.6, 0.9)
    out('パニックの悲鳴', x, 'a scream, then the crowd panics: shots fired, a fight, the stage on fire')


# ================================================================ loops in time (2026-11-02 GM: the "Hey!" should loop)
BPM = 130
BEAT = 60 / BPM
BARS = 8
LB = BEAT * 4 * BARS        # 14.77 s: 8 bars at 130 bpm, so the loop never drifts off the beat


def circ_room(x, g, rt60, wet):
    """Reverb that wraps: the tail of the end lands on the start, so a loop stays seamless."""
    ir = make_ir(g, rt60=rt60, predelay=0.01, lp_start=8000, lp_end=2500, tail_energy=0.5)
    y = convolve(np.concatenate([x, x[:ns(3.0)]]), ir)
    out = y[:len(x)].copy()
    rest = y[len(x):]
    k = 0
    while k < len(rest):
        m = min(len(rest) - k, len(x))
        out[:m] += rest[k:k + m]
        k += m
    return x + out / (np.max(np.abs(out)) + 1e-12) * np.max(np.abs(x)) * wet


def claps():
    """Single group claps (people clapping in unison), cut one by one."""
    ev = events_of(rec('clap-group-unison.mp3'), min_len=0.02, max_len=0.4, merge=0.03, tail=0.15)
    ev += events_of(rec('clap-along-no-music.mp3'), min_len=0.02, max_len=0.4, merge=0.03, tail=0.15)
    print(f'  claps: {len(ev)} events')
    return ev


def shout(g, rel, t1, n_voices, spread=0.035):
    """One recorded shout turned into a crowd: n copies, each pitched, panned and a little late."""
    x = np.zeros((ns(t1 + 0.3), 2))
    for v in range(n_voices):
        h = rec(rel, pitch=g.u(0.88, 1.1))
        h = cut(h, 0, min(t1, len(h) / SR), fin=0.003, fout=0.12)
        wrap_add(x, pan(h, g.u(-0.85, 0.85)), g.u(0, spread), g.u(0.45, 0.9))
    return x


def on_grid(g, events, beats, gain=1.0, jitter=0.012, pan_w=0.4):
    """Place one event on each given beat (0-based, counted over the whole loop)."""
    buf = np.zeros((ns(LB), 2))
    for b in beats:
        x = events[int(g.u(0, len(events)))]
        wrap_add(buf, pan(x, g.u(-pan_w, pan_w)), b * BEAT + g.u(0, jitter), gain * 10 ** (g.u(-2, 0) / 20))
    return buf


def grid_loops(p):
    g = Gen(9103)
    beats = range(BARS * 4)
    cl = claps()
    floor = bed([('roar-rock-crowd-large.mp3', 0, None)], LB, X=2.0)

    # "Hey! Hey! Hey! Hey!" on every beat, the floor clapping with it, a roar underneath
    heys = [shout(g, 'hey-men-shout.mp3', 0.6, 7) for _ in range(6)]
    h = np.zeros((ns(LB), 2))
    for b in beats:
        wrap_add(h, heys[b % len(heys)], b * BEAT, 1.0 if b % 4 == 0 else 0.8)
    c = on_grid(g, cl, beats)
    x = at(h, -21) + at(c, -27) + at(floor, -27)
    x = circ_room(x, g, 1.3, 0.3)
    export(D7 + 'ヘイの掛け声', x, -24, loop=True, ogg=True,
           note=f'{LB:.2f}s loop: "Hey!" on every beat at {BPM} bpm (8 bars), with clapping and a roar')

    # the floor clapping along on every beat (to lay under a song at 130 bpm), cheering under it
    c = on_grid(g, cl, beats) + on_grid(g, cl, beats, 0.7, 0.02, 0.8)
    s = scatter(g, LB, p['whistle'] + p['whoop'], 4, (-10, -3))
    x = at(c, -21) + at(floor, -28) + at(s, -30)
    x = circ_room(x, g, 1.1, 0.25)
    export(D7 + '曲に合わせた手拍子', x, -24, loop=True, ogg=True,
           note=f'{LB:.2f}s loop: the crowd clapping on every beat at {BPM} bpm (8 bars)')

    # the crowd singing along "Whoa-oh-oh": one recorded crowd vowel, pitched to a melody (in F)
    # (semitones from F, length in beats) for 4 bars, sung twice
    tune = [(0, 1.5), (0, 0.5), (4, 2), (2, 1.5), (0, 0.5), (-3, 2),
            (0, 1.5), (0, 0.5), (4, 1), (5, 1), (4, 1.5), (2, 0.5), (0, 2)]
    sing = np.zeros((ns(LB), 2))
    src = [rec('sing-vowel-uh-f-omni.mp3'), rec('sing-vowel-uh-f-ambeo.mp3')]
    for rep in range(2):
        t = rep * BEAT * 16
        for semi, n in tune:
            for k, y in enumerate(src):
                r = 2 ** (semi / 12)
                seg = y[ns(1.8):ns(7.0)]
                # pitch by resampling the steady part of the vowel (a higher note is also shorter; there is plenty)
                idx = np.arange(0, len(seg) - 1, r)
                seg = np.stack([np.interp(idx, np.arange(len(seg)), seg[:, ch]) for ch in range(2)], 1)
                d = n * BEAT + 0.08
                note = cut(seg, 0.1 * k, 0.1 * k + d, fin=0.06, fout=0.14)
                wrap_add(sing, pan(note, -0.5 if k == 0 else 0.5), t + g.u(0, 0.02))
            t += n * BEAT
    x = at(sing, -21) + at(floor, -28)
    x = circ_room(x, g, 1.6, 0.35)
    export(D7 + '合唱オーオー', x, -24, loop=True, ogg=True,
           note=f'{LB:.2f}s loop: the crowd singing "whoa-oh" along at {BPM} bpm (8 bars, in F)')

    # the floor jumping: the crowd lands on the first beat of every bar, roaring all the while
    jumps = [cut(rec('jump-rhythmic-300.mp3'), a, b, fin=0.01, fout=0.5)
             for a, b in [(6.7, 8.3), (13.1, 14.8), (20.6, 22.2), (33.5, 35.0)]]
    j = on_grid(g, jumps, range(0, BARS * 4, 4), 1.0, 0.01, 0.2)
    x = at(floor, -24) + at(j, -25) + at(on_grid(g, cl, beats), -32)
    export(D7 + 'フロアが跳ねる', x, -24, loop=True, ogg=True,
           note=f'{LB:.2f}s loop: the floor jumping on every bar at {BPM} bpm')


# ================================================================ crowd sizes and other scenes
def sizes(p):
    g = Gen(9104)
    L = 60.0
    # 1. nearly empty: a handful of people in a room built for hundreds. The room, a cough, now and
    #    then one person clapping or calling out
    # (the low-murmurs recording drops out in places, so the room tone is the hall murmur, far off)
    room_t = bed([('quiet-murmur-hall.mp3', 0, 40)], L)
    coughs = events_of(rec('quiet-coughs.mp3'), min_len=0.15, max_len=2.0, merge=0.2)
    one = (chunks(g, rec('clap-single-person.mp3'), 4, 2.0, 4.0)
           + [cut(rec('applause-one-person.mp3'), 0.2, 6.0, fout=1.0)]
           + [cut(rec('woo-guys.mp3'), 0, 1.1, fin=0.005, fout=0.3)])
    x = (at(lp(room_t, 1500), -38) +at(scatter(g, L, coughs, 6, (-8, 0), 0.7), -36)
         + at(scatter(g, L, one, 7, (-6, 0), 0.6), -29))
    x = room(x, g, 1.8, 0.45)
    export(D7 + '客入り1_ほぼ空', x, -27, loop=True, ogg=True, note='60s loop: a handful of people in a big room, during a song')

    # 2. sparse: twenty or so people, cheering hard to make up for it
    a = bed([('cheer-small-crowd-20.mp3', 0, 24)], L)
    b = bed([('whoops-whistles-laughter.mp3', 0.5, None)], L)
    c = scatter(g, L, events_of(rec('applause-few-people.mp3'), min_len=0.5, max_len=6, merge=0.3)
                + [cut(rec('applause-small.mp3'), 0, 4.5, fout=0.8)], 5, (-6, 0))
    x = at(a, -24) + at(b, -29) + at(c, -30)
    x = room(x, g, 1.2, 0.3)
    export(D7 + '客入り2_まばら', x, -25, loop=True, ogg=True, note='60s loop: about twenty people, during a song')

    # 3. half full: a club that is doing all right
    a = bed([('gig-small-calling-for-more.mp3', 1, None)], L)
    b = bed([('roar-applause-hall.mp3', 2, None)], L)
    s = scatter(g, L, p['whistle'] + p['whoop'], 10, (-8, 0))
    x = at(a, -23) + at(b, -30) + at(s, -29)
    export(D7 + '客入り3_半分', x, -24, loop=True, ogg=True, note='60s loop: a half-full club, during a song')

    # the quiet before the first note: the lights are down, people hush, someone coughs
    a = bed([('quiet-murmur-hall.mp3', 0, 40)], L)
    x = at(a, -27) +at(scatter(g, L, coughs, 9, (-10, 0), 0.8), -32)
    export(D7 + '演奏前の静けさ', x, -27, loop=True, ogg=True, note='60s loop: a hushed room just before the band starts')

    # outside the stage door: fans waiting, screaming when the door opens, cameras going
    a = bed([('preshow-waiting-outside.mp3', 0, None)], L)
    b = bed([('walla-exterior-event.mp3', 0, None)], L)
    cams = events_of(rec('camera-paparazzi.mp3'), min_len=0.2, max_len=3, merge=0.15)
    x = (at(a, -25) + at(b, -29) + at(scatter(g, L, p['scream'], 6, (-8, 0)), -29)
         + at(scatter(g, L, cams, 5, (-6, 0)), -31))
    export(D7 + '出待ちのファン', x, -25, loop=True, ogg=True, note='60s loop: fans waiting outside the venue, cameras and screams')

    # panic at the gig: the crowd screaming and running for the doors (loop it for as long as the scene needs)
    L2 = 36.0
    a = bed([('panic-crowd.mp3', 0.3, 11.3), ('panic-crowd.mp3', 13.2, 22.8), ('panic-crowd.mp3', 24.8, 36.5)], L2, X=1.5)
    b = bed([('panic-crowd-screaming.mp3', 0.2, 16.0)], L2, X=2.0)
    c = bed([('panic-crowd-stairs.mp3', 5.0, 24.0)], L2, X=2.0)
    run = [cut(rec('panic-running-feet.mp3'), 0, 5.0, fin=0.2, fout=0.8)]
    x = at(a, -23) + at(b, -28) + at(c, -28) + at(scatter(g, L2, run, 4, (-4, 0)), -30)
    export(D7 + 'パニック', x, -24, loop=True, ogg=True, note='36s loop: a crowd in panic, screaming and running')

    # the encore call: a whole hall chanting for the band to come back, clapping under it
    a = bed([('encore-chant-vissza.mp3', 0.0, 8.4)], 33.6, X=0.6)
    b = bed([('encore-applause-rhythmic.mp3', 0, None)], 33.6)
    x = at(a, -22) + at(b, -28)
    export(D7 + 'アンコールのコール', x, -24, loop=True, ogg=True, note='34s loop: a hall chanting for the band to come back')


if __name__ == '__main__':
    import sys
    pl = pools()
    todo = sys.argv[1:] or ['loops', 'shots', 'grid', 'sizes']
    if 'loops' in todo:
        loops(pl)
    if 'shots' in todo:
        shots(pl)
    if 'grid' in todo:
        grid_loops(pl)
    if 'sizes' in todo:
        sizes(pl)
