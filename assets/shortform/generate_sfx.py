"""Synthesize the royalty-free SFX pack (no external files/licensing — every
sound here is code, same policy as the rest of the project). Writes straight
into public/sfx/ as .wav, converts each to .mp3 via ffmpeg, deletes the .wav,
and prints the peak dB of every file (ffmpeg -af volumedetect) so a quiet one
never ships silently — see references/shortform.md's SFX table for what
"quiet" broke in the past (click2.mp3 peaked at -25dB, inaudible under speech).

Run: uv run python generate_sfx.py            → only the new sounds (default)
     uv run python generate_sfx.py --all       → regenerates EVERYTHING,
       including whoosh/pop/click — these are noise-based and not seeded, so
       a re-run writes slightly different audio each time. They're already
       tuned/approved and referenced by exact dB across many client videos
       (references/shortform.md), so leave them alone unless you mean to
       re-tune the whole pack on purpose.
"""
import sys
import numpy as np
import wave
import subprocess
import pathlib

SR = 44100
OUT = pathlib.Path(__file__).parent / "public" / "sfx"
OUT.mkdir(parents=True, exist_ok=True)
REGEN_EXISTING = "--all" in sys.argv


def save(name, y):
    y = y / (np.max(np.abs(y)) + 1e-9)
    y = np.tanh(y * 1.1)  # soft clip
    pcm = (y * 0.85 * 32767).astype(np.int16)
    wav_path = OUT / f"{name}.wav"
    with wave.open(str(wav_path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    mp3_path = OUT / f"{name}.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(wav_path), "-codec:a", "libmp3lame", "-qscale:a", "2", str(mp3_path)],
        check=True,
    )
    wav_path.unlink()
    peak = subprocess.run(
        ["ffmpeg", "-i", str(mp3_path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    max_line = next((l for l in peak.splitlines() if "max_volume" in l), "max_volume: ?")
    print(f"wrote {mp3_path.name}  {len(y) / SR:.2f}s  {max_line.strip()}")


def onepole_sweep(x, a):  # time-varying one-pole lowpass
    y = np.empty_like(x)
    prev = 0.0
    for i in range(len(x)):
        prev += a[i] * (x[i] - prev)
        y[i] = prev
    return y


# ============ existing pack (only touched with --all, see docstring) =========

if REGEN_EXISTING:
    # WHOOSH — filtered noise, cutoff opens then closes, smooth amplitude hump
    n = int(0.45 * SR); t = np.linspace(0, 1, n)
    noise = np.random.randn(n)
    a = 0.02 + 0.38 * np.sin(np.pi * t) ** 1.2  # cutoff low→high→low
    whoosh = onepole_sweep(noise, a)
    env = np.sin(np.pi * t) ** 1.4
    save("whoosh", whoosh * env)

    # POP — short tonal blip with a pitch drop + tiny transient
    n = int(0.14 * SR); t = np.linspace(0, 0.14, n)
    f = 680 * np.exp(-t * 7)  # 680→~250 Hz
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    trans = np.random.randn(n) * np.exp(-t * 120) * 0.4
    pop = (tone + trans) * np.exp(-t * 26)
    save("pop", pop)

    # CLICK — very short transient
    n = int(0.03 * SR); t = np.linspace(0, 0.03, n)
    click = np.random.randn(n) * np.exp(-t * 260)
    save("click", click)
else:
    print("skipping whoosh/pop/click (already tuned/in production) — pass --all to regenerate them too")

# ============ new pack (2026-09-04 — more SFX for more transitions/cues) ======

# RISER — rising filtered noise + rising tone, crescendo. Tension build-up
# before a reveal; place via a `sfxCues` entry a beat or two before the payoff.
n = int(1.2 * SR); t = np.linspace(0, 1, n)
noise = np.random.randn(n)
a = 0.01 + 0.5 * (t ** 1.6)  # cutoff climbs low -> high, never closes back down
ris_noise = onepole_sweep(noise, a)
f = 140 * (1 + 5.5 * t ** 1.8)  # ~140 -> ~910Hz glide up
tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.5
env = t ** 1.3  # crescendo, no decay — the payoff SFX (impact/ding) takes over
save("riser", (ris_noise * 0.8 + tone) * env)

# IMPACT — sub thump + sharp transient, for bold text/stat reveals
n = int(0.35 * SR); t = np.linspace(0, 0.35, n)
sub = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 9)
crack = np.random.randn(n) * np.exp(-t * 180) * 0.6
mid = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 14) * 0.5
save("impact", sub + crack + mid)

# GLITCH — quantized/stepped noise bursts, digital stutter. Signature SFX for
# the "glitch" cut transition (CustomGraphics.tsx GlitchLook).
n = int(0.26 * SR); t = np.linspace(0, 0.26, n)
raw = np.random.randn(n)
hold = 10  # sample-and-hold stride — the "bitcrush" sample-rate-reduction feel
crushed = np.repeat(raw[::hold], hold)[:n]
crushed = np.round(crushed * 10) / 10  # amplitude quantization
gate = (np.sin(2 * np.pi * 38 * t) > 0).astype(float)  # choppy on/off gate
save("glitch", crushed * gate * np.exp(-t * 7))

# LIGHTLEAK — slow warm swell/shimmer. Signature SFX for the "lightleak" cut
# transition (CustomGraphics.tsx LightLeakLook) — softer/longer than a whoosh.
n = int(0.9 * SR); t = np.linspace(0, 1, n)
noise = np.random.randn(n)
a = 0.015 + 0.09 * np.sin(np.pi * t) ** 1.1
swell = onepole_sweep(noise, a)
shimmer = np.sin(2 * np.pi * 1800 * t) * 0.06 * np.sin(np.pi * t)
save("lightleak", (swell * 0.9 + shimmer) * np.sin(np.pi * t) ** 1.6)

# DING — short two-tone chime/notification, for checkmarks/tips call-outs
n = int(0.5 * SR); t = np.linspace(0, 0.5, n)
ding = (np.sin(2 * np.pi * 1046.5 * t) + 0.6 * np.sin(2 * np.pi * 1568 * t)) * np.exp(-t * 7)
save("ding", ding)

# SHUTTER — camera-shutter double click, for photo-style inserts
n = int(0.12 * SR); t = np.linspace(0, 0.12, n)
c1 = np.random.randn(n) * np.exp(-t * 260)
c2 = np.zeros(n)
delay = int(0.028 * SR)
c2[delay:] = np.random.randn(n - delay) * np.exp(-t[: n - delay] * 300) * 0.75
save("shutter", c1 + c2)

# ============ pack v3 (2026-09-04b — textures reverse-engineered from a
# reference CapCut SFX pack Eduardo shared: spectrograms + volumedetect on 3
# representative files, never the files themselves, to keep the pack
# code-only/licence-free) ==========================================

# WHOOSH_METALLIC — filtered-noise sweep (like whoosh) + scattered inharmonic
# high-frequency "pings" ringing on top, for the metallic-shimmer whoosh
# character the plain whoosh doesn't have.
n = int(0.55 * SR); t = np.linspace(0, 1, n)
noise = np.random.randn(n)
a = 0.03 + 0.42 * np.sin(np.pi * t) ** 1.1
sweep = onepole_sweep(noise, a)
_rng = np.random.default_rng(3)
sparkle = np.zeros(n)
for _ in range(9):
    f0 = _rng.uniform(2200, 6200)
    s = int(_rng.uniform(0.05, 0.85) * n)
    dur = min(n - s, int(0.09 * SR))
    tt = np.arange(dur) / SR
    sparkle[s:s + dur] += np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 38) * 0.5
save("whoosh_metallic", sweep * np.sin(np.pi * t) ** 1.3 * 0.85 + sparkle)

# DROP — sustained pulsing sub-bass drop (pitch glides down, amplitude wobbles)
# — for a bass hit under a big reveal. Distinct from impact.mp3's single quick
# transient: this sustains ~1.4s.
n = int(1.4 * SR); t = np.linspace(0, 1.4, n)
f = 95 * np.exp(-t * 1.1) + 30  # 95Hz -> ~30Hz glide down
sub = np.sin(2 * np.pi * np.cumsum(f) / SR)
wobble = 1 + 0.35 * np.sin(2 * np.pi * 7 * t)
save("drop", (sub * wobble + np.random.randn(n) * 0.15) * np.exp(-t * 1.6))

# RING — a hit/slice transient followed by a long bell-like decaying tail
# (inharmonic partials, independent decay rates) — a "fancier ding" for a
# reveal that wants to ring out instead of chime quickly.
n = int(2.2 * SR); t = np.linspace(0, 2.2, n)
slice_n = int(0.04 * SR)
y = np.zeros(n)
y[:slice_n] += np.random.randn(slice_n) * np.exp(-np.linspace(0, 1, slice_n) * 40)
for f0, d in zip([880, 1480, 2350, 3120, 4010], [2.2, 3.0, 3.6, 4.2, 5.0]):
    y += np.sin(2 * np.pi * f0 * t) * np.exp(-t * d) * (0.6 / d)
save("ring", y)

# ============ pack v5 (2026-09-05 — reveal/payoff reactions) ==================

# APLAUSO — synthesized crowd applause: many short bandpassed noise "claps"
# scattered under a density envelope (sparse -> dense -> sparse) plus a
# broadband noise bed underneath so it reads as one crowd, not a drum pattern.
# For a good-news reveal beat ("você acabou de ganhar...") via `sfxCues` — not
# baked into any transition. Guarded (unlike the blocks above) so a plain
# re-run doesn't re-roll it once it exists; add --all to force a re-roll.
if REGEN_EXISTING or not (OUT / "aplauso.mp3").exists():
    dur_s = 1.6
    n = int(dur_s * SR)
    t_full = np.linspace(0, dur_s, n)
    _rng = np.random.default_rng(11)

    # broadband bed: bandpass a noise bed (two cascaded one-pole sweeps) under
    # the discrete claps, swelling in fast then settling over the tail
    bed_noise = _rng.standard_normal(n)
    bed = onepole_sweep(bed_noise, np.full(n, 0.35)) - onepole_sweep(bed_noise, np.full(n, 0.06))
    bed_env = np.clip(t_full / 0.15, 0, 1) * np.exp(-np.clip(t_full - 0.9, 0, None) * 3)
    bed = bed * bed_env * 0.22

    # discrete claps: crude highpass (diff) on a short noise burst per clap,
    # onsets drawn from a sparse->dense->sparse density envelope so the swell
    # reads as a crowd building then settling, not a metronome
    claps = np.zeros(n)
    density = lambda x: np.sin(np.pi * np.clip(x, 0, 1)) ** 0.6
    onsets = []
    while len(onsets) < 90:
        cand = _rng.uniform(0, dur_s)
        if _rng.uniform(0, 1) < density(cand / dur_s):
            onsets.append(cand)
    for onset in onsets:
        s = int(onset * SR)
        cl_len = min(int(_rng.uniform(0.008, 0.02) * SR), n - s)
        if cl_len <= 4:
            continue
        raw = _rng.standard_normal(cl_len)
        hp = np.diff(raw, prepend=0.0)  # crude highpass — crisp transient, not a thud
        tt = np.arange(cl_len) / SR
        env = np.exp(-tt * _rng.uniform(180, 320))
        claps[s:s + cl_len] += hp * env * _rng.uniform(0.5, 1.0)

    save("aplauso", bed + claps * 0.9)
else:
    print("skipping aplauso (already exists) — pass --all to re-roll it")
