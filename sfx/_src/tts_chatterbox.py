"""Chatterbox TTS (Resemble AI, MIT) for the radio voice: it has an `exaggeration` knob for emotion.
Usage: python tts_chatterbox.py <out_dir>  -> one WAV per paragraph of gen_radio.SCRIPT (24 kHz).
Runs on CPU here (no CUDA on this PC); slow but fine for a few minutes of speech.
"""
import os
import sys
import time

import torch
import torchaudio

from gen_radio import SCRIPT

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
EXAG = float(os.environ.get('CB_EXAG', '0.6'))     # 0.5 neutral, higher = more expressive
CFG = float(os.environ.get('CB_CFG', '0.35'))       # lower = faster, looser delivery
REF = os.environ.get('CB_REF')                      # optional reference voice WAV

from chatterbox.tts import ChatterboxTTS

torch.set_num_threads(max(1, os.cpu_count() - 2))
t0 = time.time()
CKPT = os.environ.get('CB_DIR', 'C:/Users/owner/Documents/models/chatterbox')  # ve.pt t3_cfg.safetensors s3gen.pt tokenizer.json conds.pt
model = ChatterboxTTS.from_local(CKPT, device='cpu')
print('model loaded in', round(time.time() - t0), 's', flush=True)
only = os.environ.get('CB_ONLY')
for i, (text, pause, speed) in enumerate(SCRIPT):
    if only and str(i) not in only.split(','):
        continue
    p = os.path.join(OUT, f'{i:02d}.wav')
    if os.path.exists(p):
        continue
    t1 = time.time()
    kw = dict(exaggeration=EXAG, cfg_weight=CFG)
    if REF:
        kw['audio_prompt_path'] = REF
    wav = model.generate(text, **kw)
    torchaudio.save(p, wav, model.sr)
    print(i, round(wav.shape[-1] / model.sr, 1), 's audio in', round(time.time() - t1), 's', flush=True)
print('done')
