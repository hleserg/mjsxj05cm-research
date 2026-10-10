#!/usr/bin/env python3
"""Весёлая чиптюн-мелодия для танца камеры. Своя, без лицензий.
Выход: WAV 16 кГц моно s16le (далее ffmpeg приведёт к формату динамика камеры).
Темп 150 BPM → доля 0.4 с; dance.sh считает движения в долях от этого же темпа.
    python3 tools/dance/tune.py out.wav [повторов=2]
"""
import sys, wave, numpy as np
SR, BPM = 16000, 150
BEAT = 60 / BPM
def f(m): return 440 * 2 ** ((m - 69) / 12)
def tone(m, beats, wave_='sq', vol=0.5, decay=6.0):
    n = int(SR * beats * BEAT); t = np.arange(n) / SR
    if m is None: return np.zeros(n)
    ph = (t * f(m)) % 1.0
    s = np.where(ph < 0.5, 1.0, -1.0) if wave_ == 'sq' else 4 * np.abs(ph - 0.5) - 1   # square / triangle
    env = np.exp(-decay * t / (beats * BEAT)) * np.minimum(1, t * 400)                   # щипок + антиклик
    return s * env * vol
def seq(notes, **kw): return np.concatenate([tone(m, b, **kw) for m, b in notes])
# C-dur, 8 тактов 4/4: мотив «та-да-дам», припев с прыжками — под повороты/кивки
C, D, E, F, G, A, B, c, d, e, g = 60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 79
melody = [(E,.5),(E,.5),(G,1),(E,.5),(D,.5),(C,1),            # такт 1-2
          (D,.5),(E,.5),(F,.5),(E,.5),(D,1),(G,1),
          (E,.5),(E,.5),(G,1),(A,.5),(G,.5),(E,1),            # такт 3-4
          (D,.5),(E,.5),(F,.5),(D,.5),(C,2),
          (c,.5),(B,.5),(A,.5),(G,.5),(A,1),(c,1),            # такт 5-6: вверх — «кивок»
          (d,.5),(c,.5),(B,.5),(A,.5),(G,2),
          (e,.5),(d,.5),(c,.5),(B,.5),(c,.5),(d,.5),(e,1),    # такт 7-8: разбег к финалу
          (g,.5),(e,.5),(c,.5),(G,.5),(c,2)]
bass_chords = [C, C, F, G, C, C, F, G, A, A, F, G, C, C, G, C]            # по полтакта
bass = np.concatenate([seq([(m - 24, .5), (m - 24, .5), (m - 12, .5), (m - 24, .5)], wave_='tri', vol=.55, decay=4) for m in bass_chords])
# ударные: «бочка» — короткий спад синуса 60 Гц, «хэт» — шум; на каждую долю, хэт на «и»
def kick(): n = int(SR * .12); t = np.arange(n) / SR; return np.sin(2 * np.pi * 60 * t * np.exp(-8 * t)) * np.exp(-25 * t)
def hat(): n = int(SR * .05); return np.random.default_rng(1).standard_normal(n) * np.exp(-np.arange(n) / SR * 120) * .25
drums = np.zeros(int(SR * BEAT * 32))
for b in range(32):
    i = int(SR * BEAT * b); k = kick(); drums[i:i + len(k)] += k if b % 2 == 0 else k * .6
    i2 = int(SR * BEAT * (b + .5)); h = hat(); drums[i2:i2 + len(h)] += h
lead = seq(melody, wave_='sq', vol=.35, decay=5)
n = min(len(lead), len(bass), len(drums)); mix = lead[:n] + bass[:n] + drums[:n]
rep = int(sys.argv[2]) if len(sys.argv) > 2 else 2
out = np.concatenate([mix] * rep + [tone(c, 2, 'sq', .35, 3)[:int(SR * BEAT * 2)] + tone(c - 12, 2, 'tri', .5, 3)[:int(SR * BEAT * 2)]])  # финальный аккорд
out = np.int16(out / np.max(np.abs(out)) * 32000)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
print(f"{sys.argv[1]}: {len(out)/SR:.1f} с, {len(out)*2} Б, темп {BPM} BPM, доля {BEAT:.3f} с, {rep}×8 тактов + финал")
