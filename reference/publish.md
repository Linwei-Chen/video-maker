# 发布指南（阶段 6）

## 1. 交付物清单（发布前必须齐）

| 文件 | 说明 |
|---|---|
| `video.mp4` | 1920×1080 / 30fps / H.264 yuv420p / faststart + AAC 192k |
| `meta.json` | {"id","title","duration_s","resolution","fps","size_mb","scenes","has_narration","voice","one_line","tech_highlights","status"} |
| `README.md` | 分镜表（幕/时长/画面/旁白/教学目标）+ 自检与修复记录 |
| `qc/f0..f7.png` | 成片均匀 8 帧（验收与封面素材） |
| `subtitles.srt` | 按旁白逐句分条的 SRT（B站 CC 用；标点感知分页实测可用） |

系列片再加：`manifest.json`（主控从各 meta.json 汇总）、`posters/<id>.jpg`（取成片 1/3 处画面）、`index.html` 观片页（读 manifest 渲染画廊卡片，脚本自行实现即可）。

## 2. B 站上传（biliup 网页接口）

**用网页接口，不用 APP 接口**（APP 接口长期 21566「投稿过于频繁」/ 601「上传过快」限流，历史最高连撞 11+ 次）。

```python
# 依赖：pip install biliup；cookies 从 cookies.json（cookie_info.cookies 展平登录态）
from biliup.plugins.bili_webup import BiliBili, Data
bili = BiliBili(Data())
bili.videos.append(BiliBili.parse_video_entry(video_path))
bili.title = "标题（≤80 字符，不能用文件路径）"
bili.desc = "简介（P 显著标签）"
bili.tid = 201            # 科普区；摄影教程用 246
bili.tags = "科普,科学,AI动画,知识"
info = bili.upload_file(video, lines='txa')   # alia 线路 DNS 不稳，固定 txa
```

工程纪律（实测沉淀）：
- **JSONL 账本**：每次尝试追加一行 `{id, ts, ok, bvid, error}`；续传判断 = 「有 bvid 即完成」，天然幂等。
- 限流自动退避：撞 21566/601/「过快」→ sleep 600s 重试；成功一支后 sleep 20~180s 再投下一支。
- 批量投稿按系列排队列，60 小时级别的窗口内慢慢熬，别抢。
- 封面：从 `qc/` 抽帧里选信息量最大的一张，`sips -s format jpeg` 转 JPEG。

### 标题/简介模板（留存验证的结构）
- **标题** = 悬念/反差钩子 + 竖线分隔 + 主题词 + 【系列编号】，例：
  - 「你的大脑一直在骗你｜三个制造错觉的漏洞【认知 01】」
  - 「《时间的形状》：13 分钟一次讲透相对论」
  - 「【AI 制作】光的本质 · 科普动画」
- **简介**开头统一一段系列定位语 → 本集要点（3~5 行）→ 发表信息/数据来源 → 代码/主页/引用提示。
- **置顶评论**：勘误与补充资料入口（发现错误先置顶说明，别删稿）。
- 标签参考：`科普,科学,AI动画,人工智能,知识` / 论文类加 `论文解读,深度学习,计算机视觉`。

## 3. 矩阵分发（可选，按内容类型联动）

| 内容 | 渠道 | 产出 |
|---|---|---|
| 论文类 | 小红书/知乎（本机装有相应发布类技能则联动） | 3:4 卡片轮播图文 / 专栏文章 |
| 通用 | 成片金句帧 → 海报图 | qc 抽帧中最美的 3~5 张做图文帖 |

## 4. 发布后闭环

- 记录 BV 号回写 meta.json / README。
- 用户反馈（评论纠错）→ 若涉及事实错误：修复 → 只重渲受影响场景 → 换稿重传（B站支持替换稿件）。
- 系列片：每集简介互链，完结后可发一篇专栏/合集总结导流。
