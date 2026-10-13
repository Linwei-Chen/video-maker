# -*- coding: utf-8 -*-
"""科普视频工厂 · 程序化氛围配乐（numpy 合成，免版权）。

生成低音铺底 + 和弦垫 + 五声音阶拨弦 + 轻噪声微光，16bit 立体声 wav。
"""

import wave

import numpy as np


def _note(freq, dur, sr, amp=0.2, attack=0.4, release=1.2, detune=0.0):
    t = np.arange(int(dur * sr)) / sr
    f = freq * (1 + detune)
    y = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) \
        + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    env = np.minimum(1, t / max(attack, 1e-3)) * \
          np.minimum(1, np.maximum((dur - t) / max(release, 1e-3), 0))
    return amp * y * env


def _reverb(sig, sr, delays=(0.09, 0.16, 0.27), gains=(0.35, 0.22, 0.12)):
    out = sig.copy()
    for d, g in zip(delays, gains):
        n = int(d * sr)
        out[n:] += g * sig[:-n]
    return out


def make_music(duration_s, out_wav, seed=42, brightness=1.0, level=0.16):
    """生成 duration_s 秒的氛围配乐。level: 0~0.3，混流时旁白为 1.0，配乐压低。"""
    sr = 44100
    rng = np.random.default_rng(seed)
    total = np.zeros(int(duration_s * sr))

    # 和弦进行（A 小调色彩，偏理性冷静）：Am9 - Fmaj7 - Cmaj9 - G6
    prog = [
        [110.0, 164.81, 220.0, 246.94, 329.63],
        [87.31, 130.81, 174.61, 220.0, 261.63],
        [65.41, 130.81, 196.0, 261.63, 329.63],
        [98.0, 146.83, 196.0, 246.94, 293.66],
    ]
    bar = 8.0  # 每和弦 8 秒
    t_cursor = 0.0
    ci = 0
    while t_cursor < duration_s:
        chord = prog[ci % len(prog)]
        dur = min(bar, duration_s - t_cursor)
        for k, f in enumerate(chord):
            sig = _note(f, dur + 1.5, sr, amp=0.5 / (k + 1.5),
                        attack=1.8, release=2.0, detune=rng.uniform(-0.001, 0.001))
            s0 = int(t_cursor * sr)
            e0 = min(s0 + len(sig), len(total))
            total[s0:e0] += sig[: e0 - s0]
        # 拨弦：五声音阶 A C D E G
        penta = [220.0, 261.63, 293.66, 329.63, 392.0, 440.0, 523.25]
        for tt in np.arange(0, dur, 1.6):
            if rng.random() < 0.75:
                f = penta[rng.integers(len(penta))] * brightness
                sig = _note(f, 2.2, sr, amp=0.14, attack=0.01, release=1.8)
                s0 = int((t_cursor + tt) * sr)
                e0 = min(s0 + len(sig), len(total))
                if e0 > s0:
                    total[s0:e0] += sig[: e0 - s0]
        t_cursor += bar
        ci += 1

    # 极低频铺底
    t = np.arange(len(total)) / sr
    total += 0.18 * np.sin(2 * np.pi * 55.0 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * t / 13.0))
    # 噪声微光（高频沙沙，非常轻）
    total += 0.008 * rng.standard_normal(len(total)) * brightness

    total = _reverb(total, sr)
    peak = np.abs(total).max()
    if peak > 0:
        total = total / peak * level
    # 头尾淡入淡出
    nf = int(3.0 * sr)
    fade_in = np.linspace(0, 1, nf); fade_out = np.linspace(1, 0, nf)
    total[:nf] *= fade_in
    total[-nf:] *= fade_out

    stereo = np.zeros((len(total), 2))
    d = int(0.012 * sr)  # 轻微立体声展宽
    stereo[d:, 0] = total[:-d] if d else total
    stereo[:-d, 1] = total[d:] if d else total
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)

    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return out_wav
