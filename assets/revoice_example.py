# -*- coding: utf-8 -*-
"""换声线重配音 · 标准配方（v2 声音方案：统一云健 zh-CN-YunjianNeural）。

适用于「src/build.py 提供 NARR（逐幕旁白文本）与 DUR（逐幕时长）」结构的主题目录。
核心步骤：① 用升级后的 narration.build_track（edge 引擎）重建旁白整轨（画面不动）
② 响度对齐旧旁白后与原配乐重混 ③ 混流替换音轨（-c:v copy，不重渲染）。
凌晨批量执行时由各主题子代理按此配方适配自身 src 结构。
"""
import os
import re
import subprocess
import sys

ASSETS = os.path.dirname(os.path.abspath(__file__))   # 本文件所在目录（assets 三件套在此）
sys.path.insert(0, ASSETS)
import factory_style as fs  # noqa: E402
import narration  # noqa: E402

TOPIC = sys.argv[1] if len(sys.argv) > 1 else ""
assert TOPIC, "用法: python assets/revoice_example.py <主题目录> [输出文件名]"
OUT_NAME = sys.argv[2] if len(sys.argv) > 2 else "video_yunjian.mp4"  # 批量时用 video.mp4 覆盖
sys.path.insert(0, TOPIC + "/src")
from build import NARR, DUR  # noqa: E402


def mean_volume(path):
    r = subprocess.run([fs.FFMPEG, "-i", path, "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"mean_volume: ([-\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def main():
    # 1. 重建旁白整轨（edge 云健，逐场景对齐原时长）
    narr_new = TOPIC + "/out/audio/narration_yunjian.wav"
    items = [(i, NARR[i]) for i in range(len(NARR)) if NARR[i].strip()]
    res = narration.build_track(items, DUR, narr_new,
                                tmpdir=TOPIC + "/out/audio/narr_edge.tmp")
    assert res, "旁白整轨构建失败"
    print("[revoice] 旁白整轨 %.2fs（目标 %.2fs）" % (fs.probe_duration(res), sum(DUR)))

    # 2. 响度对齐：新旁白平均响度对齐旧旁白（增益夹在 0.8~2.5）
    narr_old = TOPIC + "/out/audio/narration.wav"
    gain = 1.0
    if os.path.exists(narr_old):
        v_old, v_new = mean_volume(narr_old), mean_volume(narr_new)
        if v_old is not None and v_new is not None:
            gain = max(0.8, min(2.5, 10 ** ((v_old - v_new) / 20)))
            print("[revoice] 响度对齐 旧%.1fdB 新%.1fdB → 旁白增益 %.2f" % (v_old, v_new, gain))

    # 3. 与原配乐重混（沿用本主题原比例；配乐一律复用已有文件，缺失时查该主题装配脚本的 seed 重生成，勿照抄 11）
    music_wav = TOPIC + "/out/audio/music.wav"
    if not os.path.exists(music_wav):
        import music
        music.make_music(sum(DUR), music_wav, seed=11, brightness=1.0, level=0.12)
    mix_wav = TOPIC + "/out/audio/final_yunjian.wav"
    subprocess.run([fs.FFMPEG, "-y", "-loglevel", "error",
                    "-i", narr_new, "-i", music_wav,
                    "-filter_complex",
                    f"[0:a]volume={gain:.2f}[n];[1:a]volume=0.55[m];"
                    f"[n][m]amix=inputs=2:normalize=0:duration=first[a]",
                    "-map", "[a]", "-ar", "22050", "-ac", "1", mix_wav], check=True)

    # 4. 混流替换音轨（视频流直接 copy，不重渲染）
    final = TOPIC + "/" + OUT_NAME
    subprocess.run([fs.FFMPEG, "-y", "-loglevel", "error",
                    "-i", TOPIC + "/video.mp4", "-i", mix_wav,
                    "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", final], check=True)
    print("[revoice] 完成 %s  %.2fs" % (final, fs.probe_duration(final)))


if __name__ == "__main__":
    main()
