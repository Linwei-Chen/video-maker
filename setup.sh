#!/usr/bin/env bash
# video-maker 环境安装：在本技能目录创建 .venv 并安装依赖
set -euo pipefail
cd "$(dirname "$0")"

# 选一个 >=3.10 的 Python（推荐 3.12）；可用 PYTHON=xxx 覆盖
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'; then PY="$c"; break; fi
    fi
  done
fi
[ -n "$PY" ] || { echo "[setup] 未找到 Python >=3.10，请先安装"; exit 1; }

echo "[setup] 使用 $PY 创建虚拟环境 .venv/"
"$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q numpy matplotlib imageio imageio-ffmpeg edge-tts

if command -v ffmpeg >/dev/null 2>&1; then
  echo "[setup] ffmpeg: $(ffmpeg -version | head -1)"
else
  echo "[setup] 警告: 未找到 ffmpeg。macOS: brew install ffmpeg ｜ Ubuntu: sudo apt install ffmpeg"
fi

echo "[setup] 完成 ✔  渲染解释器: $(pwd)/.venv/bin/python"
echo "[setup] 验证: $(pwd)/.venv/bin/python examples/demo.py"
