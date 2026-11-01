"""08_ラジオ: a pirate-radio talk segment, in English, from the GM's script (2026-11-01).

Voice: Kokoro TTS (Apache-2.0; model files not in the repo, see gen_train.py for the download,
KOKORO_DIR points at them). Bed: a lo-fi backbeat synthesized here (kick / snare / hat through a
"cassette" lowpass with tape hiss), the FM tuning sweep and radio static from rec/hack (CC0).
The voice goes through a broadcast chain: high/low pass, a little saturation, compression.
"""
import os

import numpy as np
from scipy import signal

from dsp import SR, Gen, ns, lp, hp, bp, compress, sat, env_points, seamless, make_ir, convolve
from master import export
from gen_rec import load

KOKORO_DIR = os.environ.get('KOKORO_DIR', 'C:/Users/owner/Documents/models/kokoro')
VOICE, LANG, SPEED = 'am_onyx', 'en-us', 0.92

# One entry per paragraph; the number is the pause after it (seconds).
SCRIPT = [
    ("Hey. Neon City, after midnight. You getting this? "
     "This is Hollow Band, the junk frequency that keeps humming from the edge of town. "
     "No sponsors. No ad agency, no corporate PR desk has the guts to lean on a broadcast like this. "
     "All you get is me, a microphone, and a backbeat I pulled off an old cassette.", 1.2),
    ("So. Tonight's word is: rebuilding. ... Don't laugh. "
     "When you live between collapsed towers and burnt-out lots, anybody wants to snort at a word like that. "
     "But the Neon City Re-Building Center is seriously hungry for hands right now.", 1.0),
    ("Quote: Able-bodied citizens welcome! No experience required! Come build the future of your city! Unquote. "
     "That's the official line. Sounds like the instructions on a toy kit. "
     "What it actually means is: you sign a contract that weighs less than a hot dog wrapper, "
     "and you go roll around in rubble and dust.", 1.0),
    ("I know a nomad. Can't say the name. She answered that ad and lost an arm inside two weeks. "
     "A crane sensor glitched and the boom came down. Compensation? Come on. "
     "The second you skipped past the words 'limitation of liability', your life, your body, your cyber-insurance, all of it became your own problem. "
     "And they tell you, straight-faced: 'That was not a work incident. That was a matter of your personal health.' "
     "Funny, right?", 1.2),
    ("What's not funny is this: if we don't work there, the rubble in this city stays rubble forever. "
     "Somebody has to stand the steel up. Somebody has to pour the concrete. "
     "Otherwise the city stays a ruin.", 1.0),
    ("Quote: Decent pay! Meals provided! Sleep shelter on site! Unquote. More copy. "
     "And sure, they hand you zilico at the end of the week. There's a synth-rice lunchbox. "
     "The beds are bunks: the top one's got a busted neon tube that never stops flickering, "
     "the bottom one's got rats keeping warm. But it keeps the rain off. "
     "It keeps most of the gunfire off. Beats sleeping in an alley.", 1.2),
    ("Takes me back. Ten years ago I took a job just like it. "
     "Before dawn, with the fog still hanging, I was torquing bolts into rusted girders. "
     "The tools were so cold my fingers quit on me, and the guy next to me laughed and said: "
     "'This city's dead. We're the zombies.' "
     "Looking back, that's the day I decided to change jobs. A zombie has no future.", 1.2),
    ("And still, right now, Neon City is doing the same thing all over again. "
     "The only difference is the corporate eyes are sharper than they were. "
     "The zilico people hold the flow of currency, their subsidiaries stuff rusuru into locked vaults, "
     "and the credits we sweat for turn into cold light somewhere on an upper floor. "
     "Well. Knowing all that and working anyway isn't the worst thing you can do.", 1.0),
    ("Here's a useless little fact for you. The soup they hand out at the site canteen has a powder in it called 'reinforced yeast'. "
     "Supposed to help with muscle fatigue. What it is, is expired culture. "
     "Tastes like mold, and once your stomach gets used to it you get strangely homesick for it. "
     "Two years on, I still catch myself wanting that taste. Addictive, or just a poor man's tongue? No idea.", 1.0),
    ("... Whoops. Drifting again.", 1.2),
    ("If you heard all that and thought, 'not bad', then go to the Re-Building Center first thing tomorrow morning. "
     "A hologram receptionist will smile and ask for your signature. "
     "If you've changed your mind, now's the time to run. "
     "From the moment you sign, your life is on loan to the loan sharks upstairs, like a debt.", 1.2),
    ("Okay. That's enough on that. I'm going to put some music on and smoke-screen the whole thing. "
     "Next track is... yeah. 'Rusted Hands'. A blues, written by a guy who lost his fingers on a construction site. "
     "By the time it's over, there'll be a fresh job poster on some wall in this city.", 1.0),
    ("This has been Hollow Band, coming to you from the bottom of Neon City. "
     "Keep your ears open, choom. Catch you on the next one.", 0.0),
]


def tts():
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(KOKORO_DIR, 'kokoro-v1.0.onnx'), os.path.join(KOKORO_DIR, 'voices-v1.0.bin'))
    out = []
    for text, pause in SCRIPT:
        s, sr = k.create(text, voice=VOICE, speed=SPEED, lang=LANG)
        s = signal.resample_poly(s, SR, sr)
        out.append((s / (np.max(np.abs(s)) + 1e-12), pause))
    return out


def broadcast(y):
    """Cheap transmitter, big voice: band-limited, a little saturated, compressed hard."""
    y = hp(lp(y, 5600, 3), 140, 2)
    y = sat(y * 1.6, 1.0)
    y = compress(y, -20, 4, 0.004, 0.09)
    return y / (np.max(np.abs(y)) + 1e-12)


def backbeat(g, dur, bpm=84):
    """Lo-fi drum loop, kick / snare / hat, as if lifted from a worn cassette."""
    n = ns(dur)
    y = np.zeros(n)
    beat = 60.0 / bpm
    t = np.arange(ns(0.5)) / SR
    kick = np.sin(2 * np.pi * (45 * t + (110 - 45) * (1 - np.exp(-t * 18)) / 18 * 1.2)) * np.exp(-t * 9)
    kick = kick * env_points(len(kick), [(0, 1), (0.4, 0.3), (0.5, 0)])
    sn_n = ns(0.22)
    snare = (bp(g.r.normal(0, 1, sn_n), 900, 6000, 2) * 0.6 + np.sin(2 * np.pi * 190 * np.arange(sn_n) / SR) * 0.5) * np.exp(-np.arange(sn_n) / SR * 22)
    hat_n = ns(0.06)
    hat = hp(g.r.normal(0, 1, hat_n), 6000, 2) * np.exp(-np.arange(hat_n) / SR * 70) * 0.35
    bar = 0.0
    while bar < dur:
        for step in range(8):  # eighth notes
            tt = bar + step * beat / 2
            i = max(0, ns(tt + g.u(-0.004, 0.004)))
            if i >= n - ns(0.5):
                break
            if step in (0, 5):          # kick on 1 and the "and" of 3
                y[i:i + len(kick)] += kick[:n - i] * g.u(0.9, 1.0)
            if step in (2, 6):          # snare on 2 and 4
                y[i:i + len(snare)] += snare[:n - i] * g.u(0.8, 1.0)
            y[i:i + len(hat)] += hat[:n - i] * (g.u(0.5, 0.8) if step % 2 else g.u(0.8, 1.0))
        bar += beat * 4
    # cassette: dull top end, a bit of wow, tape hiss
    y = lp(y, 3200, 2)
    hiss = hp(g.r.normal(0, 1, n), 2500, 2) * 0.006
    return (y / (np.max(np.abs(y)) + 1e-12)) * 0.5 + hiss


def radio_show():
    g = Gen(8101)
    lines = tts()
    # layout: tuning sweep + squelch, then the talk with its pauses, then the beat alone and static
    parts, t = [], 2.6
    for s, pause in lines:
        parts.append((t, broadcast(s)))
        t += len(s) / SR + pause
    talk_end = t
    total = talk_end + 9.0
    n = ns(total)
    voice = np.zeros(n)
    for t0, a in parts:
        i = ns(t0)
        voice[i:i + len(a)] += a[:n - i]
    # the beat sits under the voice (ducked) and comes up on its own at the end
    beat = backbeat(g, total)
    duck = np.ones(n) * 0.55
    env = np.abs(signal.sosfilt(signal.butter(2, 8, 'low', fs=SR, output='sos'), np.abs(voice)))
    duck = duck - np.clip(env * 2.5, 0, 0.35)
    duck[ns(talk_end):] = np.linspace(duck[ns(talk_end)], 0.9, n - ns(talk_end))
    beat = beat * duck
    # intro: FM tuning sweep landing on the station, then a squelch; outro: static rising, then cut
    sw = load('hack/radio-fm-tuning-sweep.mp3')
    sw = sw / (np.max(np.abs(sw)) + 1e-12)
    sw = sw[ns(4.0):ns(6.4)] * env_points(ns(2.4), [(0, 0.2), (2.0, 0.8), (2.4, 0)]) * 0.5
    sq = load('hack/radio-squelch-signoff.mp3')
    sq = sq / (np.max(np.abs(sq)) + 1e-12) * 0.6
    st = load('hack/radio-static.mp3')
    st = st / (np.max(np.abs(st)) + 1e-12)
    st = st[ns(10):ns(10) + ns(5.0)] * env_points(ns(5.0), [(0, 0), (3.5, 0.6), (4.8, 0.8), (5.0, 0)]) * 0.5
    mix = np.zeros(n)
    mix[:len(sw)] += sw
    mix[ns(2.2):ns(2.2) + len(sq)] += sq[:n - ns(2.2)]
    mix += voice * 0.9 + beat
    mix[n - len(st):] += st
    # a small room so the whole thing sounds like it comes out of one speaker in one place
    ir = make_ir(g, rt60=0.3, predelay=0.004, lp_start=8000, lp_end=3000, tail_energy=0.25)
    y = convolve(np.stack([mix, mix], 1), ir)[:n]
    y = y[:n] + np.stack([mix, mix], 1) * 0.0
    export('08_ラジオ/ハロウバンド_再建の夜', y, -16, note='Hollow Band: rebuilding (English talk segment)')


if __name__ == '__main__':
    radio_show()
