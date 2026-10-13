# -*- coding: utf-8 -*-
"""video-maker 安装自检 / 展示图生成。

跑通本脚本 = 渲染管线可用。产出：
    out/demo.mp4     6 秒演示动画（1920x1080）
    out/demo.png     静帧展示图（可放 README）
"""
import os
import sys
import pathlib

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "assets"
sys.path.insert(0, str(ASSETS))
import factory_style as fs  # noqa: E402

import numpy as np  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "out"
os.makedirs(OUT, exist_ok=True)


def draw(fig, ax, t):
    fs.stars(ax, n=170, seed=42)

    # 三条辉光曲线（不同相位与颜色，缓动展开）
    x = np.linspace(0.6, 15.4, 400)
    for i, (c, ph, amp) in enumerate([(fs.CYAN, 0.0, 1.6), (fs.GOLD, 1.3, 1.1), (fs.VIOLET, 2.1, 0.7)]):
        k = fs.ease_in_out(fs.clamp((t - 0.2 - i * 0.25) / 1.6))
        if k <= 0:
            continue
        n = int(len(x) * k)
        y = 4.6 + amp * np.sin(2 * np.pi * (x * 0.09) + ph + t * 0.9)
        fs.glow_line(ax, x[:n], y[:n], c, lw=2.4 - i * 0.4)

    # 标题与公式
    fs.text_in(ax, (8, 7.9), "video-maker", t, 0.1, 0.8, size=52, color=fs.GOLD, weight=600)
    fs.text_in(ax, (8, 7.05), "把任何知识讲成一段动画", t, 0.5, 0.8, size=24, color=fs.WHITE, weight=600)
    fs.formula(ax, (8, 2.35), r'$\gamma = 1/\sqrt{1-\beta^2}$', t, 1.6, 1.0, size=30, color=fs.CYAN)
    fs.text_in(ax, (8, 1.5), "调研 → 事实表 → 审稿门 → 逐帧渲染 → 配音 → 质检 → 发布",
               t, 2.2, 0.8, size=17, color=fs.GREY)

    fs.subtitle(ax, "开源讲解动画视频工厂 · demo")


if __name__ == "__main__":
    mp4 = str(OUT / "demo.mp4")
    fs.render_scene(draw, 6.0, mp4, fps=30, progress_tag="demo")
    fs.grab_frame(mp4, 3.0, str(OUT / "demo.png"))
    print("[demo] 完成:", mp4, "和 out/demo.png")
