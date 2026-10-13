# -*- coding: utf-8 -*-
"""科普视频工厂 · 共享设计系统与渲染管线。

所有场景脚本 import 本模块，保证全系列统一的视觉语言与交付格式。
用法（场景脚本）:
    import sys, pathlib
    ASSETS = pathlib.Path(__file__).resolve().parent      # 本文件所在的 assets 目录
    sys.path.insert(0, str(ASSETS))
    import factory_style as fs
"""

import math
import os
import shutil
import subprocess

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

# ---------------------------------------------------------------- 设计系统 --
BG      = "#070B14"   # 深空底色
BG_SOFT = "#0E1526"   # 次级面板
GOLD    = "#FFC864"   # 主强调：光、能量、章节
CYAN    = "#5FD7FF"   # 科学元素：光线、场
PINK    = "#FF6B9D"   # 对比、警示、"错误"概念
VIOLET  = "#9D7BFF"   # 时空、抽象概念
GREEN   = "#7CFFB2"   # 生命、成功、正确
WHITE   = "#FFFFFF"
GREY    = "#9BA3B5"   # 注释文字
DARKGREY= "#3A4256"

FONT_CN = ["PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Source Han Sans SC",
           "WenQuanYi Micro Hei", "Microsoft YaHei", "Songti SC", "SimHei", "Arial Unicode MS"]
# macOS 自带前两者；Linux 需安装 Noto/文泉驿 CJK 字体，Windows 用微软雅黑
plt.rcParams["font.sans-serif"] = FONT_CN
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["mathtext.fontset"] = "cm"

W, H, FPS = 19.2, 10.8, 30          # 1920x1080 @30fps（吃力可降 24）
FFMPEG = shutil.which("ffmpeg") or "/usr/local/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/usr/local/bin/ffprobe"


# ---------------------------------------------------------------- 缓动函数 --
def clamp(t, a=0.0, b=1.0):
    return max(a, min(b, t))

def ease_in_out(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2

def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3

def ease_in(t):
    t = clamp(t)
    return t ** 3

def ease_out_back(t, s=1.7):
    t = clamp(t)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2

def lerp(a, b, t):
    return a + (b - a) * clamp(t)

def pulse(t, period=1.0):
    return 0.5 + 0.5 * math.sin(2 * math.pi * t / period)


# ---------------------------------------------------------------- 画布工具 --
def new_fig():
    """新建 1920x1080 深空画布，返回 (fig, ax)。"""
    fig = plt.figure(figsize=(W, H), dpi=100, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16), ax.set_ylim(0, 9)
    ax.axis("off")
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)
    return fig, ax

def _rgb(h):
    """'#RRGGBB' → (r,g,b) 0..255 元组。"""
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, t):
    """两种hex颜色按 t 混合，返回 hex。"""
    a, b = _rgb(c1), _rgb(c2)
    return "#%02x%02x%02x" % tuple(int(round(a[i] + (b[i] - a[i]) * clamp(t))) for i in range(3))


def stars(ax, n=140, seed=7, alpha=0.5, t=None):
    """背景星点。t 给定时星点按各自相位缓慢闪烁（呼吸感）。"""
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 16, n); y = rng.uniform(0, 9, n)
    s = rng.uniform(1, 14, n); a = rng.uniform(0.08, alpha, n)
    if t is not None:
        ph = rng.uniform(0, 2 * np.pi, n)
        a = a * (0.65 + 0.35 * np.sin(2 * np.pi * t / 6 + ph))
    ax.scatter(x, y, s=s, c="white", alpha=np.clip(a, 0.02, 1), linewidths=0, zorder=0)


def nebula_bg(ax, seed=7, strength=0.55, grid=True):
    """多层星云渐变背景（深空蓝紫）。任何 t>2s 的画面不得是纯色底。"""
    rng = np.random.default_rng(seed + 1)
    lo = 24   # 低分辨率渐变场，imshow 双线性放大即成柔和星云
    h_img = max(int(lo * 9 / 16), 8)
    tints = np.array([[0.05, 0.09, 0.20], [0.10, 0.06, 0.22],
                      [0.04, 0.12, 0.22], [0.02, 0.04, 0.10]])
    centers = rng.uniform(0, 1, (len(tints), 2))
    widths = rng.uniform(0.25, 0.7, len(tints))
    jj, ii = np.meshgrid(np.linspace(0, 1, lo), np.linspace(0, 1, h_img))
    img = np.zeros((h_img, lo, 3))
    for k, c in enumerate(tints):
        d = np.exp(-(((jj - centers[k][0]) ** 2 + (ii - centers[k][1]) ** 2) / widths[k]))
        img += c * (0.25 + d)[..., None]
    img = np.clip(img / len(tints) * 1.4, 0, 1)
    ax.imshow(img, extent=[0, 16, 0, 9], origin="lower", alpha=strength,
              interpolation="bicubic", zorder=0, aspect="auto")
    if grid:
        for gx in np.arange(1, 16, 1.6):
            ax.plot([gx, gx], [0, 9], color="#1C2942", lw=0.5, alpha=0.35, zorder=0)
        for gy in np.arange(1, 9, 1.6):
            ax.plot([0, 16], [gy, gy], color="#1C2942", lw=0.5, alpha=0.35, zorder=0)


def camera(ax, t, seed=0, amp=0.10, period=11.0):
    """镜头缓慢漂移（呼吸感）。draw_fn 内先画背景后、画主体前调用。"""
    rng = np.random.default_rng(seed + 2)
    dx = amp * math.sin(2 * math.pi * t / period + rng.uniform(0, 6))
    dy = amp * 0.6 * math.sin(2 * math.pi * t / (period * 1.4) + rng.uniform(0, 6))
    ax.set_xlim(0 + dx, 16 + dx)
    ax.set_ylim(0 + dy, 9 + dy)


def grad_rect(ax, x, y, w, h, c_top, c_bottom=None, zorder=2):
    """垂直渐变矩形（替代扁平色块柱）。c_bottom 缺省为主色加深。"""
    if c_bottom is None:
        c_bottom = mix(c_top, "#000000", 0.55)
    cols = np.linspace(np.array(_rgb(c_bottom), float), np.array(_rgb(c_top), float), 64)
    img = (cols[:, None, :] / 255.0 * np.ones((1, 2, 1)))
    ax.imshow(img, extent=[x, x + w, y, y + h], origin="lower",
              interpolation="bicubic", zorder=zorder, aspect="auto")


def chip(ax, xy, s, color=GOLD, size=15, pad=0.28, t=None, t0=0.0, dur=0.5, zorder=11):
    """带底色的标签芯片（用于阶段/要点标签）。返回 text artist。"""
    a = ease_in_out((t - t0) / dur) if t is not None else 1.0
    if a <= 0.01:
        return None
    x, y = xy
    tw = max(len(s) * size * 0.011, 1.2)
    ax.add_patch(plt.Rectangle((x - tw / 2 - pad, y - pad * 0.8), tw + 2 * pad, pad * 1.6,
                               facecolor=mix(color, "#000000", 0.72), edgecolor=color,
                               lw=1.0, alpha=0.9 * a, zorder=zorder))
    return ax.text(x, y, s, fontsize=size, color=WHITE, alpha=a, ha="center", va="center",
                   zorder=zorder + 1, fontweight=600)


def trail(ax, x, y, color, lw=2.2, tail=0.35, zorder=3):
    """运动拖尾：曲线前段按低 alpha 铺底、尾段全亮，形成'正在生长'的视觉。"""
    n = len(x)
    head = max(int(n * (1 - tail)), 2)
    ax.plot(x[:head], y[:head], color=color, lw=lw * 0.8, alpha=0.16, zorder=zorder)
    ax.plot(x[head - 1:], y[head - 1:], color=color, lw=lw, alpha=0.85,
            solid_capstyle="round", zorder=zorder)


def beat(t, t0, dur):
    """节拍进度门：返回该节拍内的 0→1 进度（未开始 0，结束保持 1）。"""
    return ease_in_out((t - t0) / dur) if t >= t0 else 0.0

def ease_in_back(t, s=1.70158):
    """回撤进场（anticipation 内建于曲线：先反向蓄力再冲出）。"""
    t = clamp(t)
    return (s + 1) * t ** 3 - s * t ** 2

def ease_out_elastic(t):
    """弹性出台（活泼对象点缀；严肃图表慎用）。"""
    t = clamp(t)
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return 2 ** (-10 * t) * math.sin(-(10.5 * t - 0.75) * 2 * math.pi / 3) + 1

def there_and_back(t):
    """三角包络：值升到 1 再回落（Indicate/脉冲类注意力动画的标准包络）。"""
    tri = 1 - abs(2 * clamp(t) - 1)
    return ease_in_out(tri)

def flash_pt(ax, xy, t, t0, color=GOLD, n=12, length=0.30, r0=0.06, dur=0.9, zorder=12):
    """放射线闪耀（Manim Flash 语义）：'这里有东西发生！'的一次性惊叹号。"""
    u = clamp((t - t0) / dur, 0.0, 1.0)
    if u <= 0.0 or u >= 1.0:
        return
    x, y = xy
    grow = ease_out(u)
    fade = 1 - u
    for k in range(n):
        ang = 2 * math.pi * k / n
        r1 = r0 + grow * length
        r2 = r1 + 0.22 * length * fade
        ax.plot([x + r1 * math.cos(ang), x + r2 * math.cos(ang)],
                [y + r1 * math.sin(ang), y + r2 * math.sin(ang)],
                color=color, lw=2.2 * fade + 0.4, alpha=0.9 * fade,
                solid_capstyle="round", zorder=zorder)

def spark_burst(ax, xy, t, t0, color=CYAN, n=26, v0=2.4, seed=7, dur=0.8,
                gravity=1.0, s0=40, zorder=12):
    """粒子迸发（爆发时刻/数据揭晓的豪华惊叹号）。确定性种子，解析式轨迹纯函数。"""
    u = (t - t0) / dur
    if u <= 0:
        return
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 2 * np.pi, n)
    spd = v0 * rng.uniform(0.30, 1.0, n) ** (1 / 3)     # 幂律→球面均匀感
    life = rng.uniform(0.55, 1.0, n)
    k = 2.2                                              # 阻尼：位移=v/k·(1-e^{-k·u})
    disp = spd * (1 - np.exp(-k * u)) / k * (dur * 2.2)
    px = xy[0] + disp * np.cos(ang)
    py = xy[1] + disp * np.sin(ang) - gravity * (u * dur) ** 2 * 0.5
    vis = u < life
    if not vis.any():
        return
    a = np.clip((1 - u / life), 0, 1) ** 2 * vis
    ax.scatter(px, py, s=s0 * (0.3 + 0.7 * (1 - u)) * vis, c=color,
               alpha=0.9 * a, linewidths=0, zorder=zorder)

def count_in(ax, xy, val, t, t0, dur=1.0, fmt="{:.0f}", size=40, color=WHITE,
             weight=600, suffix="", zorder=10):
    """数字滚动到目标值后定格（数据揭晓标准件）。t<t0 不画。"""
    if t < t0:
        return None
    k = ease_out(clamp((t - t0) / dur, 0.0, 1.0))
    shown = val * k
    s = (fmt.format(val) if k >= 0.999 else fmt.format(shown)) + suffix
    return ax.text(*xy, s, fontsize=size, color=color, ha="center", va="center",
                   fontweight=weight, zorder=zorder)

def glow_line(ax, x, y, color, lw=2.2, zorder=3, layers=(0.10, 0.22, 0.5)):
    """多层描边模拟辉光曲线。x,y 为等长数组。"""
    for f, a in zip((3.2, 2.0, 1.0), layers):
        ax.plot(x, y, color=color, lw=lw * f, alpha=a, solid_capstyle="round", zorder=zorder)

def glow_scatter(ax, x, y, color, s=14, zorder=3, layers=(0.12, 0.5)):
    for f, a in zip((3.5, 1.0), layers):
        ax.scatter(x, y, s=s * f * f, c=color, alpha=a, linewidths=0, zorder=zorder)

def text_in(ax, xy, s, t, t0=0.0, dur=0.8, size=22, color=WHITE, weight="normal",
            ha="center", va="center", zorder=10, alpha_max=1.0):
    """随时间淡入的文本，返回 artist（t<t0 时不画）。"""
    a = ease_in_out((t - t0) / dur) * alpha_max if t >= t0 else 0.0
    if a <= 0.01:
        return None
    return ax.text(*xy, s, fontsize=size, color=color, alpha=a, ha=ha, va=va,
                   fontweight=weight, zorder=zorder)

def subtitle(ax, s, alpha=1.0):
    """底部字幕条（全程必备）。s 为当前句字幕。"""
    if not s:
        return
    ax.add_patch(plt.Rectangle((2.0, 0.32), 12.0, 0.78, color="#000000",
                               alpha=0.42 * alpha, zorder=8, lw=0))
    ax.text(8.0, 0.71, s, fontsize=17.5, color=WHITE, alpha=alpha, ha="center",
            va="center", zorder=9)

def chapter_card(ax, num, title_cn, title_en, t, dur=1.6):
    """章节卡片：大编号 + 中英文标题，金色细线。"""
    a = ease_in_out(min(t / (dur * 0.35), 1.0)) * ease_in_out(max(1 - (t - dur * 0.75) / (dur * 0.25), 0))
    if a <= 0.01:
        return
    ax.add_patch(plt.Rectangle((0, 0), 16, 9, color="#000000", alpha=0.55 * a, zorder=6, lw=0))
    ax.text(8.0, 5.4, num, fontsize=64, color=GOLD, alpha=a, ha="center", va="center",
            fontweight=600, zorder=7)
    ax.plot([5.2, 10.8], [4.35, 4.35], color=GOLD, lw=1.1, alpha=0.75 * a, zorder=7)
    ax.text(8.0, 3.6, title_cn, fontsize=34, color=WHITE, alpha=a, ha="center",
            va="center", fontweight=600, zorder=7)
    ax.text(8.0, 2.75, title_en, fontsize=15, color=GREY, alpha=0.9 * a, ha="center",
            va="center", zorder=7)

def formula(ax, xy, s, t, t0=0.0, dur=1.0, size=30, color=WHITE, zorder=10):
    """mathtext 公式淡入。s 形如 r'$E = mc^2$'。"""
    return text_in(ax, xy, s, t, t0, dur, size=size, color=color, zorder=zorder)


# ---------------------------------------------------------------- 渲染管线 --
def render_scene(draw_fn, duration, out_mp4, fps=FPS, progress_tag=""):
    """渲染一个场景。

    draw_fn(fig, ax, t) 在时刻 t（秒）绘制整帧画面（自行决定要不要清空重画:
    本函数每帧前会 ax.cla() 并重置坐标，draw_fn 只管画内容）。
    用 canvas 缓冲直接取像素，比 savefig 快数倍。
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_mp4)), exist_ok=True)
    tmpdir = out_mp4 + ".frames"
    os.makedirs(tmpdir, exist_ok=True)
    n_frames = int(round(duration * fps))
    fig, ax = new_fig()
    import imageio.v2 as imageio
    paths = []
    for i in range(n_frames):
        t = i / fps
        ax.cla()
        ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")
        ax.set_facecolor(BG)
        draw_fn(fig, ax, t)
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
        p = os.path.join(tmpdir, f"f{i:05d}.png")
        imageio.imwrite(p, buf)
        paths.append(p)
        if i % 60 == 0 and progress_tag:
            print(f"[render]{progress_tag} {i}/{n_frames}", flush=True)
    plt.close(fig)
    _encode(paths, out_mp4, fps)
    shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"[done]{progress_tag} -> {out_mp4}", flush=True)


def _encode(frame_paths, out_mp4, fps):
    enc = "libx264"
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-r", str(fps),
           "-f", "image2pipe", "-vcodec", "png", "-i", "-",
           "-c:v", enc, "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_mp4]
    # 用管道喂帧，避免大量临时文件重复 IO
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as proc:
        import imageio.v2 as imageio
        for p in frame_paths:
            proc.stdin.write(open(p, "rb").read())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg 编码失败: {out_mp4}")


def concat_scenes(scene_mp4s, out_mp4, reencode=False):
    """拼接场景片段为成片。默认 -c copy；时长异常时 reencode=True。"""
    lst = out_mp4 + ".list.txt"
    with open(lst, "w") as f:
        for p in scene_mp4s:
            f.write(f"file '{os.path.abspath(p)}'\n")
    if reencode:
        cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
               "-i", lst, "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", out_mp4]
    else:
        cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
               "-i", lst, "-c", "copy", "-movflags", "+faststart", out_mp4]
    subprocess.run(cmd, check=True)
    os.remove(lst)

def mux_audio(video_mp4, audio_wav, out_mp4):
    """把旁白/配乐混流进成片（视频流直接拷贝）。"""
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", video_mp4, "-i", audio_wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_mp4],
                   check=True)

def probe_duration(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())

def grab_frame(video_mp4, t_sec, out_png):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", str(t_sec), "-i", video_mp4,
                    "-frames:v", "1", out_png], check=True)

def make_blindset(video_mp4, scene_bounds, out_dir, n_per_scene=2, seed=7,
                  crop_bottom=0.15):
    """生成盲测美感门的帧集：每幕避开首尾各 2s 抽 n 帧，并裁掉底部字幕条。

    scene_bounds: [(幕名, 起始秒, 结束秒), ...]，与分镜表/meta.json 一致。
    裁字幕是关键：字幕会把旁白语义白送给审稿人，让画面本身的空洞被文字掩盖。
    把 out_dir 交给**不知视频主题**的独立 Agent 评审（规程见 reference/visual-and-engine.md §7）。
    """
    import imageio.v2 as imageio
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    total = probe_duration(video_mp4)
    paths = []
    for name, t0, t1 in scene_bounds:
        t1 = min(t1, total)
        lo, hi = t0 + 2.0, max(t0 + 2.5, t1 - 2.0)
        if hi - lo < 0.5:                                   # 幕太短：只取幕中点
            ts = [(t0 + t1) / 2]
        else:
            ts = sorted(rng.uniform(lo, hi, size=n_per_scene).tolist())
        for k, t in enumerate(ts, 1):
            p = os.path.join(out_dir, f"blind_{name}_{k}.png")
            grab_frame(video_mp4, t, p)
            img = imageio.imread(p)
            imageio.imwrite(p, img[: int(img.shape[0] * (1 - crop_bottom))])
            paths.append(p)
    print(f"[blindset] {len(paths)} 帧 -> {out_dir}", flush=True)
    return paths
