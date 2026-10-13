# video-maker · 开源讲解动画视频工厂

<p align="center">
  <img src="docs/demo.png" width="720" alt="video-maker demo">
</p>

<p align="center">
  <strong>给它一篇论文、一个网页、一个主题或一个概念，它还你一支可以直接上传 B 站的讲解动画。</strong><br>
  调研 → 事实表 → 审稿门 → 逐帧渲染 → 配音配乐 → 三层质检 → 发布
</p>

video-maker 是一个 [ZCode](https://zcode.ai) 技能（也可以脱离 ZCode 单独当 Python 工具库用）。它把一条经过数十支成片验证的科普动画生产流水线固化成了 AI 可执行的工作流：从事实核查到逐帧渲染，从配音到 B 站上传，每个环节都有硬性质量门。

---

## ✨ 特性

- **全自动流水线**：输入主题 → 深度调研并建事实表（所有数字必须溯源，禁止编造）→ 旁白分镜 → 渲染 → 配音 → 成片
- **程序化逐帧渲染**：matplotlib 引擎（~12 帧/秒），确定性纯函数 `render(t)`，固定种子可复现，2× 超采样抗锯齿
- **统一视觉系统**：星云渐变背景 + 渐变柱体 + 三层辉光曲线 + 运动拖尾 + 镜头漂移 + 章节卡 + 底部字幕条，开箱即是「科普片质感」而非 PPT 画面
- **纪录片级配音**：edge-tts 云健（zh-CN-YunjianNeural），逐句自动提速适配场景时长，断流废片自动重试，断网熔断回退 macOS say
- **程序化配乐**：numpy 合成氛围音乐（和弦垫 + 五声音阶拨弦），免版权、可复现
- **双重质量门**：缺陷门（乱码/遮挡/空洞/构图，每幕 ≥1 帧抽检）+ **美感门三问**（这帧当插画及格吗？遮住字幕在讲故事吗？和 3B1B 同框丢人吗？）；无论发生什么必须交付可播成片
- **前沿技法库内置**：3B1B 源码美学（颜色即身份/公式四态/动作-呼吸节拍）、动效参数表（anticipation/stagger/转场六式）、爆款叙事实证（Muller 误区前置千人实验、MrBeast 留存分区、TED-Ed 三方审校）、20 种程序化视觉技法（FBM/域扭曲/Bloom/电影调色/合成音效）
- **发布配方内置**：B 站 biliup 网页接口上传、限流退避、封面选取、SRT 字幕、标题/简介模板
- **踩坑知识库**：50+ 条「病症→病理→处方」格式的视频方法论——什么是好视频（七条判据）、什么是坏视频（病历本）、坏了怎么修（检修模式），全部来自真实制作实践（详见 [`reference/pitfalls.md`](reference/pitfalls.md)）

## 🚀 快速开始

### 方式 A：作为 ZCode 技能（推荐）

```bash
# 1. 克隆到 ZCode 技能目录
git clone https://github.com/Linwei-Chen/video-maker.git ~/.agents/skills/video-maker

# 2. 安装环境
cd ~/.agents/skills/video-maker && bash setup.sh

# 3. 在 ZCode 里直接说：
#    「用 video-maker 把『相对论』做成一个讲解动画视频」
#    「把这篇论文（附件/arXiv链接）做成视频」
```

### 方式 B：脱离 ZCode，当 Python 引擎用

```bash
git clone https://github.com/Linwei-Chen/video-maker.git
cd video-maker && bash setup.sh
.venv/bin/python examples/demo.py   # 渲染 6 秒演示片 + 展示图，跑通即安装成功
```

在自己的场景脚本里使用引擎三件套：

```python
import sys, pathlib
sys.path.insert(0, "/path/to/video-maker/assets")
import factory_style as fs   # 设计系统 + 渲染管线
import narration, music      # 配音 + 配乐

def draw(fig, ax, t):        # 每一帧都会被调用，t 为场景内秒数
    fs.stars(ax, seed=42)
    fs.text_in(ax, (8, 6.5), "你好，世界", t, 0, 1, size=44, color=fs.GOLD, weight=600)
    fs.subtitle(ax, "每一帧都是一个纯函数")

fs.render_scene(draw, 8.0, "out/s00.mp4", fps=30)     # 渲染单场景
narration.build_track([(0, "你好，这是旁白。")], [8.0], "out/narr.wav")  # 配音整轨
music.make_music(8.0, "out/music.wav", seed=11)        # 程序化配乐
fs.mux_audio("out/s00.mp4", "out/narr.wav", "out/video.mp4")
```

### 系统要求

| 依赖 | 说明 |
|---|---|
| Python ≥ 3.10（推荐 3.12） | `setup.sh` 自动建 venv |
| ffmpeg / ffprobe | macOS: `brew install ffmpeg`；Ubuntu: `sudo apt install ffmpeg` |
| 网络 | edge-tts 配音需要联网；macOS 断网可回退 `say`（Linux/Windows 无回退） |
| 中文字体 | macOS 自带 PingFang SC；Linux 装 Noto Sans CJK SC；Windows 微软雅黑（引擎内置回退列表） |
| 平台 | macOS 完整支持（作者的开发与验证平台）；Linux/Windows 渲染主体可用，`say` 兜底与部分发布细节需自行适配 |

## 🏭 工作流（技能如何工作）

```
立项 → ① 调研建事实表 → ② 文案分镜 + 审稿门 → ③ 引擎选型 → ④ 逐帧制作
                                                                    ↓
     发布（B站/社媒） ← ⑥ 交付与打包 ← ⑤ 三层质量门（静帧自检 → 独立验收 → 修复复检）
```

| 阶段 | 关键纪律 | 放行条件 |
|---|---|---|
| ① 调研 | 事实表逐条注明出处；拿不准宁可不写；**禁止编造** | facts.md 覆盖全部入片数字 |
| ② 文案 | 冷开场钩子（前 5 秒必须有真信息）；每幕 48~60 字；比喻先行、术语后置 | **大模型审稿门全票满意**（曾有单集磨 9 轮） |
| ③ 选型 | 默认 matplotlib；精制长片走 Canvas+CDP；点名 3B1B 风格才上 Manim（需 arm64 原生环境） | 引擎决策表落定 |
| ④ 制作 | 先渲 3 张静帧目检再全量；场景首帧禁全黑；每幕 ≤3 信息焦点；t≤2s 主体在位 | 全场景渲染完成 |
| ⑤ 质检 | 成片均匀抽 8 帧逐帧 Read + 独立验收 Agent；修复只重渲受影响场景 | 无 medium 以上瑕疵 |
| ⑥ 交付 | 1920×1080/30fps/H.264 + meta.json + README 分镜表 + SRT | 可直接上传 |

详细规范见 [`SKILL.md`](SKILL.md)（工作流主文件）与 [`reference/`](reference/)：

| 文件 | 内容 |
|---|---|
| [`reference/cutting-edge.md`](reference/cutting-edge.md) | 前沿技法库：3B1B 源码美学、动效参数表、爆款叙事实证（误区前置/留存分区）、20 种程序化视觉技法与音效合成 |
| [`reference/research-script.md`](reference/research-script.md) | 调研方法、事实表模板、旁白量化写作规范、审稿门操作 |
| [`reference/visual-and-engine.md`](reference/visual-and-engine.md) | 视觉系统、四条引擎路线（matplotlib / Canvas+CDP / WebCodecs / Manim）、音频配方 |
| [`reference/pitfalls.md`](reference/pitfalls.md) | 50+ 条踩坑清单，每条背后是一次真实事故 |
| [`reference/publish.md`](reference/publish.md) | B 站上传配方、标题/简介模板、封面规范、矩阵分发 |

## 🎨 设计决策（为什么是现在这套方案）

这些决策都有明确的理由，完整的利弊分析在 pitfalls.md 的病历本里：

- **matplotlib 逐帧，而不是 Manim** —— Manim 环境脆弱（依赖需源码编译、转译环境必死）；matplotlib 原生 arm64 实测 ~12 帧/秒、API 稳定、AI 子代理失败率最低。Manim 路线保留给明确点名 3B1B 风格的场景（文档含源码编译 cairo 的完整配方）。
- **edge-tts 神经语音，而不是系统合成音** —— 系统 say 类合成音一出戏观众就走；工程上内置三重防线：断流废片校验重试、语速 4 档自动适配、连续失败熔断回退。
- **配音时长反驱场景时长** —— 「画面淡没了配音还在念」是系统性缺陷的根因；先合成配音，超长就精简文案或拉长场景。
- **字幕纯白无描边** —— 描边会吞掉 3~4px 宽的中文笔画（笔画密的字直接残缺，看似重影）。
- **确定性纯函数渲染** —— `render(t)` + 固定种子，任何一帧可独立复现、可并行、可增量修复。
- **镜头设计表 + 黄金镜头先行** —— 每幕拆 3~6 个节拍、标注高光时刻；最具代表性的一镜先做到"能上热门"的水平才许铺开全片（防止"分镜直接跳代码、每幕退化成元素淡入"）。
- **独立视觉验收 Agent** —— 制作者自检会有盲区；抽帧交给一个只看图的独立 Agent，判"乱码/遮挡/空洞/构图"之外还要过"美感三问"，medium 以上回炉。

## 📁 目录结构

```
video-maker/
├── SKILL.md                 # 技能主文件：六阶段工作流 + 红线速查（AI 读这个）
├── setup.sh                 # 一键环境安装
├── assets/                  # 可直接复用的引擎三件套（已测试）
│   ├── factory_style.py     #   设计系统 + 渲染管线 + QC 工具
│   ├── narration.py         #   旁白引擎（edge-tts 云健 + say 兜底）
│   ├── music.py             #   程序化配乐（numpy 合成）
│   └── revoice_example.py   #   换声线重配音标准配方（画面零重渲）
├── reference/               # 深度工艺文档（按需读）
├── examples/demo.py         # 安装自检 + 展示图生成
└── docs/demo.png            # 展示图
```

## 🎬 成片规格

本流水线产出的成片统一为：1920×1080 / 30fps / H.264 (yuv420p, faststart) + AAC，中文旁白 + 程序化配乐 + 逐句字幕。`examples/demo.py` 六秒演示片可一览默认视觉系统（星云背景 / 渐变主体 / 辉光曲线 / 注意力动画）。

## ⚠️ 已知限制

- `say` 兜底仅 macOS；Linux/Windows 需保证 edge-tts 可联网
- B 站上传配方依赖 [biliup](https://github.com/biliup/biliup) 与账号登录态，接口可能随时间变化
- 程序化配乐是「氛围底噪」级别，不追求音乐性
- 引擎面向 2D 讲解动画；3D 渲染不在范围内

## 🤝 贡献

欢迎提 Issue / PR：新场景组件、新引擎路线、TTS/ASR 集成、更多平台发布配方都很有价值。修改 `assets/` 后请跑 `examples/demo.py` 确认渲染管线不回归。

## 📄 许可证

[MIT](LICENSE)
