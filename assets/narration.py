# -*- coding: utf-8 -*-
"""科普视频工厂 · 中文旁白生成（edge-tts 云健 主引擎 + macOS say 断网兜底）。"""

import contextlib
import os
import shutil
import subprocess
import sys
import time
import wave

import factory_style as fs

# 统一品牌声线：微软神经语音「云健」（zh-CN-YunjianNeural，纪录片男声）。
# 需要网络；连续失败自动回退 macOS say（音质降级但保证交付）。
DEFAULT_VOICE = "zh-CN-YunjianNeural"

EDGE = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "edge-tts")
if not os.path.exists(EDGE):
    EDGE = shutil.which("edge-tts") or "edge-tts"

# 旧 say 声线（兜底用；旧脚本传入这些名字会被归一到云健）
VOICES = [
    "Reed (中文（中国大陆）)",
    "Flo (中文（中国大陆）)",
    "Eddy (中文（中国大陆）)",
    "Tingting",
]
SAY = "/usr/bin/say"

_edge_fails = 0            # 连续失败计数（进程内熔断器）
_EDGE_FAIL_LIMIT = 3


def edge_alive():
    """熔断器：连续失败达上限后，本进程内不再尝试 edge-tts，直接走 say。"""
    return _edge_fails < _EDGE_FAIL_LIMIT


def synth_edge(text, out_mp3, voice=None, rate="+0%", tries=3):
    """edge-tts 合成单句旁白（mp3），带重试与熔断。返回 bool。"""
    global _edge_fails
    if not edge_alive():
        return False
    voice = voice or DEFAULT_VOICE
    os.makedirs(os.path.dirname(os.path.abspath(out_mp3)), exist_ok=True)
    for i in range(tries):
        try:
            subprocess.run([EDGE, "--voice", voice, "--rate", rate, "--text", text,
                            "--write-media", out_mp3],
                           check=True, timeout=120,
                           stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 2000 \
               and fs.probe_duration(out_mp3) > 0.3:
                _edge_fails = 0
                return True
        except Exception:
            time.sleep(2 + 3 * i)
    _edge_fails += 1
    return False


def synth(text, out_aiff, voice=None, rate=None):
    """（兜底）macOS say 合成单句旁白，返回 bool。voice 为 None 时按 VOICES 顺序自动兜底。"""
    os.makedirs(os.path.dirname(os.path.abspath(out_aiff)), exist_ok=True)
    cand = [voice] if voice else VOICES
    for v in cand:
        cmd = [SAY, "-v", v, "-o", out_aiff]
        if rate:
            cmd += ["-r", str(rate)]
        cmd.append(text)
        try:
            subprocess.run(cmd, check=True, timeout=120,
                           stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            if os.path.exists(out_aiff) and os.path.getsize(out_aiff) > 2000 \
               and fs.probe_duration(out_aiff) > 0.3:
                return True
        except Exception:
            continue
    return False


def to_wav(src, dst_wav):
    subprocess.run([fs.FFMPEG, "-y", "-loglevel", "error", "-i", src, dst_wav], check=True)


def _dur_wav(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / w.getframerate()


def synth_fit(text, out_wav, scene_dur, voice=None, margin=0.6):
    """edge-tts 合成一句并自动提速适配场景时长（句尾留白 ≥ margin 秒）。

    返回 (ok, 合成时长, 所用语速)；网络失败返回 (False, 0, "")，调用方回退 say。
    中文语速上限约 8 字/秒，合成结果短于 文案长度×0.10s 视为断流废片，自动重试。
    多档提速后仍超长时照常返回实际时长，由调用方裁尾（保底不阻塞交付）。
    """
    limit = max(scene_dur - margin, 0.8)
    floor = max(1.0, len(text) * 0.10)
    rate = "+0%"
    mp3_p = out_wav + ".mp3"
    best = (False, 0.0, "")
    for _ in range(4):
        if not synth_edge(text, mp3_p, voice=voice, rate=rate):
            return best
        to_wav(mp3_p, out_wav)
        d = _dur_wav(out_wav)
        if d < floor:
            continue  # 断流废片 → 同语速重试
        best = (True, d, rate)
        if d <= limit:
            break
        need = d / limit
        step = max(8, min(35, int(round((need - 1) * 100))))
        cur = int(rate.strip("+%") or 0)
        rate = f"+{min(cur + step, 45)}%"
    with contextlib.suppress(OSError):
        os.remove(mp3_p)
    return best


def build_track(items, scene_durations, out_wav, voice=None, rate=None, tmpdir=None,
                engine="edge"):
    """按场景合成旁白并拼接为整片音轨。

    items: [(scene_index, 文本), ...]  scene_index 从 0 计
    scene_durations: [float, ...] 各场景时长（秒），音轨逐场景精确对齐
    engine: "edge"（默认，云健神经语音，逐句自动提速适配时长）
            "say"  （macOS 本地合成，断网兜底）
    voice: engine="edge" 时传 None 或旧 say 声线名都会归一到 DEFAULT_VOICE
    返回 out_wav 路径；全部失败返回 None（调用方退回纯字幕方案）。
    tmpdir: 中间文件目录
    """
    if engine == "edge":
        # 旧任务书/旧脚本传入的 say 声线名统一归到云健
        if voice is None or voice in VOICES or "中文" in str(voice):
            voice = DEFAULT_VOICE
    tmpdir = tmpdir or (out_wav + ".tmp")
    os.makedirs(tmpdir, exist_ok=True)
    pieces = []
    for idx, dur in enumerate(scene_durations):
        match = [t for i, t in items if i == idx]
        text = " ".join(match)
        wav_p = os.path.join(tmpdir, f"n{idx:02d}.wav")
        ok = False
        if text.strip():
            if engine == "edge":
                ok, used, used_rate = synth_fit(text, wav_p, dur, voice=voice)
                if ok and used > dur:
                    print(f"[narration] 场景{idx} 旁白超长 {used:.1f}s > {dur:.1f}s，已裁尾",
                          flush=True)
            if not ok:  # edge 失败（熔断/断网）→ say 兜底
                aiff_p = os.path.join(tmpdir, f"n{idx:02d}.aiff")
                say_voice = voice if engine == "say" else None
                if synth(text, aiff_p, voice=say_voice, rate=rate):
                    to_wav(aiff_p, wav_p)
                    ok = True
        if not ok:
            # 该场景无旁白（合成失败或无文本）→ 补场景时长静音
            subprocess.run([fs.FFMPEG, "-y", "-loglevel", "error",
                            "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
                            "-t", str(dur), wav_p], check=True)
        else:
            # 裁剪/补静音到场景时长（apad + -t 同时完成截断与补齐）
            tmp2 = wav_p + ".pad.wav"
            subprocess.run([fs.FFMPEG, "-y", "-loglevel", "error", "-i", wav_p,
                            "-af", "apad", "-t", f"{dur:.3f}",
                            "-ar", "22050", "-ac", "1", tmp2], check=True)
            os.replace(tmp2, wav_p)
        pieces.append(wav_p)

    lst = os.path.join(tmpdir, "list.txt")
    with open(lst, "w") as f:
        for p in pieces:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run([fs.FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", out_wav], check=True)
    if fs.probe_duration(out_wav) > 1.0:
        return out_wav
    return None
