# Local Screen Translator（Windows）

[English](README.md) | [中文](README_zh.md)

离线本地 OCR 翻译叠加层，适合游戏、视频与界面文本的实时翻译。

## 许可

Apache-2.0，见 `LICENSE` 与 `NOTICE`。

## 功能概览

- 框选屏幕区域（ROI）+ 置顶字幕叠加层
- PaddleOCR（PP‑OCRv5）支持日文/英文识别
- NLLB‑200 高质量离线翻译（ja -> zh）
- 可选文本钩子（剪贴板）与 YouTube 字幕桥接
- 上下文窗口显示最近的原文/译文

## 快速开始

1) 创建虚拟环境并安装依赖

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) 安装 PaddlePaddle（择一）

```powershell
# GPU（CUDA 11.8）
python -m pip install paddlepaddle-gpu==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

# CPU
python -m pip install paddlepaddle==3.2.2
```

3) 下载 OCR 模型（PP‑OCRv5 det + rec）

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\download_ppocrv5_models.py
```

4) 下载翻译模型（推荐 NLLB‑200）

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\download_ct2_nllb.py
```

5) 运行

```powershell
.\.venv\Scripts\Activate.ps1
python .\app\main.py
```

使用上次选区（跳过框选）：

```powershell
python .\app\main.py --use-last
```

## 模式

- OCR（默认）：屏幕区域 OCR + 实时翻译
- Text Hook：读取剪贴板（Textractor 等）
- Captions：YouTube 字幕桥接（HTTP）

可在控制窗口切换，或修改 `config/default.json` 的 `input.mode`。

## 翻译引擎

默认 NLLB‑200 distilled（`facebook/nllb-200-distilled-600M`），`jpn_Jpan -> zho_Hans`。

可选回退：

OPUS‑MT 级联（ja->en->zh）：

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\download_ct2_opus_mt.py --model Helsinki-NLP/opus-mt-ja-en
python .\scripts\download_ct2_opus_mt.py --model Helsinki-NLP/opus-mt-en-zh
```

Argos（CPU，质量较低）：

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\install_argos_model.py --from ja --to zh
```

## 文本钩子（Textractor）

适合视觉小说等 OCR 效果不佳的场景。

1) Textractor 连接游戏进程并找到可用 hook
2) 启用 Clipboard 扩展（Extensions -> Clipboard）
3) 设置 `input.mode` 为 `text_hook_clipboard`，或在控制窗选择 Text Hook

可用配置项：
- `input.clipboard_poll_ms`
- `input.text_hook_app_path`（前台进程或目录限制）
- `input.text_hook_debug`

## YouTube 字幕桥接

1) 安装 Tampermonkey
2) 导入 `plugins/youtube_caption_bridge.user.js`
3) 设置 `input.mode` 为 `caption_http`
4) 打开 YouTube 字幕

字幕会 POST 到 `http://127.0.0.1:8765/caption`。

## GPU/CUDA 提示

- PaddleOCR GPU 使用 CUDA 11.8 的 wheel
- CTranslate2 GPU 需要 CUDA 12 runtime（`cublas64_12.dll`）
- 缺少 CUDA 12 时会自动回退到 CPU int8

## 常见问题

- 一直 “Waiting for OCR” 通常是选区/显示器索引不匹配，建议重新框选
- 游戏字幕请尽量只框住字幕条，减少干扰元素
- 若系统缩放不是 100%，可设置 `FORCE_DPI_AWARENESS=1` 再启动

## 目录结构

```
app/        # 主程序与流水线控制
capture/    # DXcam 捕获
ocr/        # OCR 引擎
translate/  # CT2/NLLB 翻译
ui/         # 选区/叠加/控制/上下文窗口
config/     # 默认配置（用户配置不进库）
```
