# 视觉系统与引擎指南（阶段 3~4 详细操作）

## 1. 视觉设计系统（全套已沉淀在 assets/factory_style.py）

### 调色板（深夜深空蓝基调，直接用常量）
`BG #070B14` 深空底 ｜ `GOLD #FFC864` 光/能量/章节强调 ｜ `CYAN #5FD7FF` 光线/场 ｜ `PINK #FF6B9D` 对比/警示 ｜ `VIOLET #9D7BFF` 时空/抽象 ｜ `GREEN #7CFFB2` 生命/成功 ｜ `GREY #9BA3B5` 注释 ｜ 白 `#E8EDF5` 正文

### 核心组件（factory_style API，import 后直接用）
```python
import sys; sys.path.insert(0, "/path/to/video-maker/assets")  # 即本技能 assets 目录（参考 assets/factory_style.py 文件头示例，可用 __file__ 定位）
import factory_style as fs
import narration, music

fs.new_fig()                    # 19.2×10.8 画布，坐标系固定 0..16 × 0..9
fs.stars(ax, n=140, seed=42, t=t)   # 背景星点（t= 时缓慢闪烁）
fs.glow_line(ax, x, y, color, lw)   # 三层描边辉光线条
fs.glow_scatter(...)            # 双层光晕粒子
fs.text_in(ax, xy, s, t, t0, dur, size, color, weight=600)  # 淡入文本
fs.formula(ax, xy, r'$\gamma=1/\sqrt{1-\beta^2}$', t, t0, dur, size)  # mathtext 公式
fs.subtitle(ax, "旁白字幕")      # 底部半透明字幕条（全程存在）
fs.chapter_card(ax, "01", "标题", "ENGLISH", t, dur)  # 章节卡
fs.render_scene(draw_fn, dur_s, out_mp4, fps=30)      # draw_fn(fig,ax,t)，内部已清屏
fs.concat_scenes([s0, s1...], out) / fs.mux_audio(v, wav, out)
fs.probe_duration(v) / fs.grab_frame(v, t, png)
缓动：fs.ease_in_out / ease_out / ease_out_back / lerp / clamp / pulse
```

### 精美化组件（防"PPT 画面"，每帧都该用到其中几个）
```python
fs.nebula_bg(ax, seed, grid=True)   # 星云渐变+细网格背景——禁止纯色底当背景
fs.camera(ax, t, seed, amp=0.1)     # 镜头缓慢漂移（呼吸感），画完背景后调用
fs.grad_rect(ax, x, y, w, h, c_top) # 垂直渐变柱/面板——禁止纯色扁平矩形当主体
fs.chip(ax, (x,y), "标签", color)   # 带底色描边的标签芯片
fs.trail(ax, x, y, color, lw)       # 曲线"正在生长"拖尾（前段淡、头部亮）
fs.beat(t, t0, dur)                 # 节拍进度门 0→1，编排多元素时序的标准件
fs.mix(c1, c2, t) / fs._rgb(hex)    # 颜色混合工具
```

### 注意力动画原语（有语义才用，参考 cutting-edge.md §A3）
```python
fs.flash_pt(ax, (x,y), t, t0)           # 放射线闪耀 = "这里有东西发生！"（Manim Flash）
fs.spark_burst(ax, (x,y), t, t0, color) # 粒子迸发 = 爆发/诞生时刻（幂律速度+重力，固定种子）
fs.count_in(ax, (x,y), 299792, t, t0, fmt="{:,}")  # 数字滚动定格 = 数据揭晓
fs.there_and_back(u)                    # 来回包络 = Indicate 类温和强调
fs.pulse(t, period)                     # 脉动 = 对象"活着"（呼吸/闪烁）
fs.ease_in_back(u) / fs.ease_out_elastic(u)  # 回撤进场（自带 anticipation）/ 弹性出台
```

**分层构图标准写法**（每幕的 draw_fn 模板）：
```python
def draw(fig, ax, t):
    fs.nebula_bg(ax, seed=SCENE_SEED)        # 1 背景层
    fs.stars(ax, n=160, seed=SCENE_SEED, t=t)
    fs.camera(ax, t, seed=SCENE_SEED)        # 2 镜头呼吸
    # 3 中景主体：grad_rect/glow_line/trail/formula，按镜头设计表的节拍时序进场
    # 4 前景：chip 标签、text_in 标注、高光闪烁
    fs.subtitle(ax, chunk)                   # 5 字幕条最后画
```

### 构图铁律（盲评与验收提炼）
- 每幕 ≤3 个信息焦点；**t≤2s 主体必须在位**；任何 t>2s 画面不得大面积空黑（建议开场 0.4/1.2/2.0s 三段式入场，不要 4.5s 才出主体）
- 开场与尾声**满构图落版**（居中主文案 + 系列署名）
- 文字不压图形；低对比文字白字+黑底垫（panel/描边提亮）
- 主视觉要够大（曾修过主图只占 7% 画面的案例）；每幕第 0 帧背景必须满帧可见

## 2. 渲染纪律（matplotlib 主路线）

1. 场景 = 纯函数 `sNN(ax, t, dur)`，NARR（旁白）+ DUR（时长）两个列表是唯一事实源，写 assert：`dur >= len(文本)/4.5 + 1.5`
2. 所有随机 `np.random.default_rng(seed)` 固定种子，可复现
3. **先渲 3 张关键静帧**（`build.py still 幕:时刻 ...`）Read 自检 → 修正 → 再全量
4. 逐场景渲染 `out/scenes/sNN.mp4`：实测 ~12 帧/秒；**单条 Bash ≤8 分钟、一次一个渲染进程**，超时按场景拆
5. 帧提取直接 `fig.canvas.buffer_rgba()`（比 savefig 快数倍）；`if i % 60 == 0: print(flush=True)` 打进度
6. concat 默认 `-c copy`，时长异常才 reencode；混流 `-c:v copy` 保护已渲画面
7. build.py 命令约定：`still` / `scene N` / `info`（时长核算表）/ `assemble`

## 3. 引擎路线 B：Canvas 2D + Chrome CDP（精制长片）

路线配方（实测 18 帧/秒，可稳定产出 13 分钟级长片）：
- 单页 HTML + Canvas 2D，**2× 超采样**（内部 3840×2160 → 输出 1080p）
- Node 22 原生 WebSocket 直连 Chrome CDP（headless，`--no-proxy-server` 防系统代理劫持 127.0.0.1），`Page.captureScreenshot` 截 **JPEG** 帧（比 PNG 快一倍+，比 Playwright 8fps → 18fps）
- 多章并行：子代理各自 `cp -r` 到 /tmp 沙箱 + 独立 CDP 端口（8345~8348），交付拷回
- 配音驱动时长：`durations.json` → TIMING_OVERRIDES（新时长 = max(原时长, 音频+1.7s)）→ **淡出必须相对 `seg.dur` 写，禁止写死绝对时刻**
- ffmpeg 编码 CRF18 + AAC 192k + faststart
- 引擎注意：text()/line() 要继承 globalAlpha；ease_out_back(0) 有浮点粉尘需 clamp

## 4. 引擎路线 C：Canvas + WebCodecs（论文深讲/真实数据）

路线配方（系列成片实测，音画对齐误差 0ms）：
- 浏览器内 WebCodecs（avc1.640028 12Mbps）+ mp4-muxer 直接出 MP4，跳过帧序列落盘
- `lib/fft.js` radix-2 FFT 做**真频谱实验室**（讲信号/频率/图像处理必用：讲频率却没有真实频谱图，观众一眼看穿内容空洞）
- `lib/tex.js` matplotlib mathtext 预渲染公式精灵贴图（浏览器排版公式不稳的解法）
- 3B1B 调色板 + 全局摄像机系统（平移/缩放过场）
- 结构模板：冷开场真失败案例 → 现象 → 为什么 → 怎么改 → 提升多少 → 你能接着做什么

## 5. 引擎路线 D：Manim（仅用户点名时）

- **必须**：原生 arm64 Python 3.12 venv；pycairo 无 macOS 轮子 → 从源码编译最小化 cairo（pixman 0.44.2 + cairo 1.18.4，禁 xlib/freetype 后端）到独立 prefix
- **禁止**：在转译（Rosetta）或老旧 Python 环境尝试（实测无法完成交付）
- Manim 特有坑：FadeOut 对 always_redraw 无效（先 clear_updaters）；字幕禁深色描边；逐章独立渲染 + concat

## 6. 音频配方（照抄，勿改）

### 旁白（assets/narration.py，edge-tts 云健主引擎）
```python
narration.build_track([(0, NARR[0]), (1, NARR[1]), ...], DUR, "out/audio/narration.wav")
# 自动：逐句合成 → 断流废片检测重试（< 字数×0.10s）→ 语速自动适配（句尾留白 ≥0.6s，+8%~+45%）
#     → apad/截断到场景时长 → concat 整轨；连续失败熔断回退 say（status 记 degraded）
```
- 默认声线 **zh-CN-YunjianNeural**（云健，纪录片男声；系统合成音出戏，仅作断网兜底）；女性向内容可用 XiaoxiaoNeural（晓晓）
- 需要网络；直连若间歇断流，给 edge-tts 配置本机代理环境变量（HTTPS_PROXY）可显著提高成功率
- **配音时长反驱**：合成完检查每幕 `语音 X.Xs / 场景 X.Xs`；超长 → 精简文案（不砍场景）；大量场景被拉长 → 更新 DUR 重算时间线

### 配乐（assets/music.py，numpy 程序化，免版权）
```python
music.make_music(总时长s, "out/audio/music.wav", seed=<每片指定>, brightness=0.7~1.3, level=0.12)
# Am9–Fmaj7–Cmaj9–G6 和弦垫 + 五声音阶拨弦 + 55Hz 低频铺底 + 混响，头尾 3s 淡入淡出
```

### 混音（照抄）
```bash
ffmpeg -i narration.wav -i music.wav -filter_complex \
  "[0:a]volume=1.35[n];[1:a]volume=0.5[m];[n][m]amix=inputs=2:normalize=0:duration=first[a]" \
  -map "[a]" -ar 22050 -ac 1 out/final_audio.wav
```
- **禁用 apad 无限填充**（它可在无人察觉间写满磁盘）；侧链闪避可选：`sidechaincompress=threshold=0.02:ratio=7`
- 终检可选 `loudnorm -16 LUFS`

### 换声/改配音（不动画面）
用 assets/revoice_example.py 配方：重建旁白整轨 → ffmpeg volumedetect 响度对齐（增益 0.8~2.5）→ 复用原配乐按原比例重混 → `-c:v copy` 混流替换，原片备份。

## 7. 盲测美感门操作规程（阶段 5 照此执行，不得简化）

**为什么必须盲测**：作者和知情的评审都知道每幕想讲什么，看空洞画面会自动脑补出语义——实测一支"全部门通过"的成片，盲测下 14 幕里大半答不出"这帧在讲什么"。画面好不好，只有**不知道答案的眼睛**能判断。

### 工具

```python
fs.make_blindset("video.mp4",
                 [("s00", 0, 16), ("s01", 16, 50), ...],   # 幕边界，照抄 meta.json/分镜表
                 "qc/blind", n_per_scene=2)
# 每幕避开首尾各 2s 随机抽 2 帧、裁掉底部字幕条，输出 qc/blind/blind_sNN_k.png
```

### 验收 Agent 派发（提示词模板，原样使用）

派一个有 Read 能力的独立 Agent，**只给帧文件路径列表**，不读 plan/facts/script，提示词：

```
你是信息流里最没有耐心的观众。下面的图片截自一支你没有看过的视频，字幕已被裁掉。
对每一帧【先答后评，禁止猜测主题后反向解释】：
1. see：画面里客观有什么？（罗列元素）
2. guess：你认为它在讲什么概念？不确定就写"猜不出"。
3. info：只看图形本身（忽略图中文字），它单独传达了多少论点？（0=纯装饰）
4. stop：信息流里刷到它——停下还是划走？
5. score：1~10 分（7 分 = 头部科普频道的普通一帧）。
你的任务是找出观众划走的理由，禁止善意脑补。
输出 JSON：[{"file": ..., "see": ..., "guess": ..., "info": ..., "stop": ..., "score": ...}]
```

### 判定

- `guess` 答不出/答错，或 `info` ≈ 0，或 `score` < 7 → 该帧所属幕 **FAIL**；
- FAIL 幕的处理是**重设计主视觉**（该幕画面必须能独立回答"这帧在讲什么"），不是修补缺陷；
- 全片通过率 < 80% → 不是个别幕的问题，是镜头设计表的问题，回阶段 3 重做；
- 任何修复后**全量重测**；只复查修复点的复检无效（病历本 E5）。

### 纪律

- 审稿人不读任何项目文档；主控不得在派发时泄露主题、幕标题、旁白文本；
- 验收记录（含 JSON 原文）存 `docs/reviews/blind.md`，作为成片交付的一部分；
- 盲测门与缺陷门相互独立：缺陷门 PASS 不构成盲测门的任何证据。
