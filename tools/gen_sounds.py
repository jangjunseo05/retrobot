"""기억 재현용 효과음을 절차적으로 생성한다 (외부 에셋 불필요).

    python tools/gen_sounds.py
→ assets/sounds/*.wav (16-bit mono, 22050 Hz, 루프 재생용 6초)
"""
import math
import os
import random
import struct
import wave

RATE = 22050
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sounds")
rng = random.Random(7)


def write(name, samples):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}.wav")
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 30000)) for s in samples))
    print("wrote", os.path.normpath(path))


def lowpass(samples, a):
    out, y = [], 0.0
    for s in samples:
        y += a * (s - y)
        out.append(y)
    return out


def noise(n):
    return [rng.uniform(-1, 1) for _ in range(n)]


def tone(freq, dur, amp=0.5, decay=4.0):
    n = int(RATE * dur)
    return [amp * math.sin(2 * math.pi * freq * i / RATE) * math.exp(-decay * i / RATE) for i in range(n)]


def mix_into(buf, part, start):
    for i, s in enumerate(part):
        if start + i < len(buf):
            buf[start + i] += s


def seconds(t):
    return int(RATE * t)


def radio_static(dur=6):
    n = seconds(dur)
    hiss = lowpass(noise(n), 0.5)
    hum = [0.08 * math.sin(2 * math.pi * 120 * i / RATE) for i in range(n)]
    # 멀리서 들리는 옛 노래 같은 느린 멜로디
    melody = [0.0] * n
    notes = [392, 440, 494, 440, 392, 330, 349, 392]
    for k, f in enumerate(notes):
        mix_into(melody, tone(f, 0.7, 0.18, 1.5), seconds(k * 0.75))
    return [0.25 * h + m + melody[i] for i, (h, m) in enumerate(zip(hiss, hum))]


def rain(dur=6):
    n = seconds(dur)
    base = lowpass(noise(n), 0.15)
    buf = [0.5 * s for s in base]
    for _ in range(400):
        mix_into(buf, [0.3 * rng.uniform(-1, 1) * math.exp(-i / 40) for i in range(200)], rng.randrange(n))
    return buf


def birds(dur=6):
    n = seconds(dur)
    buf = [0.03 * s for s in lowpass(noise(n), 0.05)]
    for _ in range(10):
        start, f0 = rng.randrange(n - seconds(0.4)), rng.uniform(2500, 4200)
        chirp = [0.25 * math.sin(2 * math.pi * (f0 + 1500 * math.sin(i / 300)) * i / RATE) * math.exp(-8 * i / RATE)
                 for i in range(seconds(0.25))]
        mix_into(buf, chirp, start)
    return buf


def music_box(dur=6):
    n = seconds(dur)
    buf = [0.0] * n
    notes = [784, 659, 659, 698, 587, 587, 523, 587, 659, 698, 784, 784]
    for k, f in enumerate(notes):
        mix_into(buf, tone(f, 1.0, 0.35, 3.0), seconds(k * 0.5))
        mix_into(buf, tone(f * 2, 0.6, 0.08, 5.0), seconds(k * 0.5))
    return buf


def school_bell(dur=6):
    n = seconds(dur)
    buf = [0.0] * n
    for k, f in enumerate([659, 523, 587, 392, 392, 587, 659, 523]):
        mix_into(buf, tone(f, 0.9, 0.4, 2.0), seconds(k * 0.6))
    return buf


def waves(dur=6):
    n = seconds(dur)
    base = lowpass(noise(n), 0.08)
    return [0.9 * s * (0.3 + 0.7 * (0.5 + 0.5 * math.sin(2 * math.pi * i / seconds(3)))) for i, s in enumerate(base)]


def crickets(dur=6):
    n = seconds(dur)
    buf = [0.0] * n
    t = 0.0
    while t < dur - 0.2:
        pulse = [0.15 * math.sin(2 * math.pi * 4500 * i / RATE) * (1 if (i // 220) % 2 == 0 else 0)
                 for i in range(seconds(0.12))]
        mix_into(buf, pulse, seconds(t))
        t += rng.uniform(0.3, 0.6)
    return buf


def clock_tick(dur=6):
    n = seconds(dur)
    buf = [0.0] * n
    for k in range(int(dur)):
        for off, amp in ((0.0, 0.5), (0.5, 0.35)):
            mix_into(buf, [amp * rng.uniform(-1, 1) * math.exp(-i / 60) for i in range(600)], seconds(k + off))
    return buf


def beep():
    return tone(880, 0.12, 0.4, 10) + tone(1320, 0.12, 0.4, 10)


if __name__ == "__main__":
    for fn in (radio_static, rain, birds, music_box, school_bell, waves, crickets, clock_tick, beep):
        write(fn.__name__, fn())
