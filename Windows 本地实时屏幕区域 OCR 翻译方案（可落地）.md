# Windows 本地实时屏幕区域 OCR 翻译方案（可落地）

## 1. 目标与范围

**目标**

- 用户在 Windows 上选择屏幕某个矩形区域（ROI）。
- 系统以较高频率采集该区域画面，进行**英文 OCR**提取文本。
- 对识别到的英文文本进行**本地离线翻译（英→中）**。
- 以**透明置顶叠加层**或侧边浮窗实时展示翻译结果。
- 全流程本地运行，不依赖外部网络（可选更新模型时才联网）。

**典型场景**

- 浏览器页面（视频字幕、Canvas 渲染、图片文本、PDF 截图）
- 游戏/软件界面英文提示
- 会议共享屏幕/教学视频字幕等

------

## 2. 总体架构

数据流（推荐的工程拆分）：

1. **采集层（Screen Capture）**
2. **预处理层（图像增强 + 变化检测）**
3. **OCR 层（文字检测/识别）**
4. **文本后处理层（合并、去抖、缓存）**
5. **翻译层（本地 NMT 推理）**
6. **展示层（透明置顶叠加 / 浮窗）**

示意：

- DXcam(ROI 截屏) → OpenCV/NumPy 预处理 → RapidOCR(ONNXRuntime) → 文本合并/去抖 → 翻译（Argos 或 CTranslate2+OPUS）→ PySide6 叠加渲染

------

## 3. 技术选型（Windows 推荐组合）

### 3.1 屏幕采集：DXcam（优先）

选择原因：**Windows 专用高性能**、支持 Direct3D 独占全屏捕获、支持截取指定区域 ROI，并可在内部线程持续采集。DXcam 文档明确说明它基于 Windows Desktop Duplication API，且支持通过 `region=(left,top,right,bottom)` 截取指定区域，并提供 start/get_latest_frame 的采集模式。[GitHub](https://github.com/ra1nty/DXcam)

- 优势：高帧率、低延迟、对全屏应用/游戏更友好。[GitHub](https://github.com/ra1nty/DXcam)
- 备选：`python-mss`（跨平台、MIT），但在 Windows 高帧率/全屏兼容性上通常不如 DXcam。[GitHub+1](https://github.com/BoboTiG/python-mss?utm_source=chatgpt.com)

------

### 3.2 OCR：RapidOCR（ONNXRuntime 推理，优先）

选择原因：更偏“离线部署/工程化”，且可不依赖完整 Paddle 运行时（如只用 onnxruntime 版本），适合做桌面实时应用。

RapidOCR 官方说明：

- 旨在将 PaddleOCR 模型转换为 ONNX 并在多语言/多平台推理；
- 默认支持中文与英文，强调“快速离线部署”；
- 工程脚本 Apache-2.0，且注明 OCR 模型版权归属（Baidu）。[GitHub](https://github.com/RapidAI/RapidOCR)

> 备注：你如果追求“效果最强、功能最全”，也可直接用 PaddleOCR（Apache-2.0，宣称支持 100+ 语言），但依赖更重、打包更复杂。[GitHub](https://github.com/PaddlePaddle/PaddleOCR)

------

### 3.3 本地翻译：两条可落地路线（推荐优先 A）

#### A 方案（最快落地）：Argos Translate（推荐默认）

Argos Translate 是离线翻译库（Python），支持安装 `.argosmodel` 模型包，且说明其翻译基于 OpenNMT；同时它也提供 GPU 加速开关（通过环境变量把 device 类型传给 CTranslate2）。[GitHub](https://github.com/argosopentech/argos-translate)

- 适合：**先跑通闭环**、快速上线可用版本
- 体验：对短句/UI/字幕通常够用；长段落可能不如大模型自然

许可证：项目在 GitHub 标注 MIT，并在 README 里提到双许可（MIT/CC0）。[GitHub](https://github.com/argosopentech/argos-translate)

#### B 方案（更高性能/更可控）：CTranslate2 + OPUS/Marian 模型

CTranslate2 是专门做 Transformer 推理加速的库（C++/Python），强调量化、融合、CPU/GPU 高效推理，并采用 MIT license。[GitHub](https://github.com/OpenNMT/CTranslate2)
 你可以选用 **Helsinki-NLP OPUS-MT en→zh** 模型（Hugging Face 上标注 License: apache-2.0），并把 Transformers/Marian 模型转换到 CTranslate2 格式后进行推理。[Hugging Face+1](https://huggingface.co/Helsinki-NLP/opus-mt-en-zh)

- 适合：追求更低延迟、更稳定吞吐、可做 int8/FP16 等量化
- 成本：模型转换、模型管理、工程复杂度更高

------

### 3.4 展示与交互：PySide6（Qt for Python）透明置顶叠加

建议用 **PySide6** 而不是 PyQt5，核心原因是**分发/商业化的许可证风险更低**：

- Qt for Python（PySide6）官方说明可用 LGPLv3/GPLv3/商业许可；PyPI 也注明开源许可包含 LGPLv3。[Qt Documentation+1](https://doc.qt.io/qtforpython-6/?utm_source=chatgpt.com)
- PyQt5 在 PyPI 明确写的是 GPLv3（以及商业许可）。如果你未来希望闭源分发，PyQt 路线可能要额外评估/购买授权。[PyPI+1](https://pypi.org/project/PyQt5/?utm_source=chatgpt.com)

实现透明置顶/无边框：使用 Qt 的 window flags（置顶、无边框等）。[Qt Documentation+1](https://doc.qt.io/qt-6/qtwidgets-widgets-windowflags-example.html?utm_source=chatgpt.com)
 实现“点击穿透”：可用 `Qt.WA_TransparentForMouseEvents` 等属性让叠加层不抢鼠标事件（不影响用户点浏览器/游戏）。[Stack Overflow+1](https://stackoverflow.com/questions/17968267/how-to-make-click-through-windows-pyqt?utm_source=chatgpt.com)

------

## 4. 关键功能设计

### 4.1 ROI 区域选择（用户指定区域）

提供两种模式：

- **屏幕坐标模式（最简单）**：用户按热键进入“选区模式”，全屏半透明遮罩，拖拽矩形保存 ROI（left, top, right, bottom）。
- **跟随窗口模式（增强）**：用户先点选目标窗口（如 Chrome），ROI 存为“窗口内相对坐标”。当窗口移动/缩放时通过 Win32 获取窗口位置动态修正 ROI。

落地建议：先做屏幕坐标模式，稳定后再加窗口跟随。

------

### 4.2 实时流水线（多线程/队列）

避免 UI 卡顿，推荐线程划分：

- Capture 线程：DXcam 持续采集 ROI（target_fps 30/60），只保留最新帧（丢帧而非积压）。DXcam 本身提供 start/get_latest_frame 的采集方式。[GitHub](https://github.com/ra1nty/DXcam)
- OCR 线程：对“变化帧”做 RapidOCR 推理
- Translate 线程：对“文本变化”做翻译
- UI 线程：渲染叠加层（Qt 主线程）

核心原则：**采集快、识别慢，必须解耦**；并且必须“只处理最新的一帧/最新的一句”。

------

### 4.3 变化检测与去抖（实时体验的关键）

为了“看起来实时”但又不爆 CPU/GPU，建议加入以下策略：

- **图像变化检测**：对 ROI 做快速 hash / 灰度缩放差分；变化小则跳过 OCR。
- **文本稳定器**：
  - OCR 结果做 normalize（去多余空格、统一标点/大小写策略）
  - 与上次文本做相似度比较（如 Levenshtein/ratio），小变化不触发翻译
- **翻译缓存**：同一句英文重复出现时直接命中缓存（字幕/按钮极常见）
- **节流**：翻译层可以设最小间隔（例如 150–300ms 级别），避免“每帧翻译”

------

### 4.4 OCR 后处理（让翻译更自然）

OCR 通常会返回多个文本框：

- 需要按 y/x 排序并合并为行
- 对英文常见断行做处理（如行尾连字符、换行合并）
- 对 UI 类短句可按“句子/行”翻译，对长段落按“句子分割”翻译

------

### 4.5 翻译输出与显示方案

推荐提供 2 种显示模式（用户可切换）：

1. **字幕条模式**（最通用）
   - 叠加层固定在 ROI 下方或屏幕底部
   - 显示“最近一句翻译”
   - 不尝试逐字覆盖原文，工程最简单、体验稳定
2. **旁注模式**（适合网页阅读）
   - ROI 附近显示一个浮窗，支持复制、滚动
   - 适合长段落（否则字幕条会溢出）

逐框覆盖（“把中文贴在英文原位置”）也能做，但需要更复杂的排版与遮挡策略，建议作为 v2 功能。

------

## 5. 环境与部署方案

### 5.1 运行环境

- OS：Windows 10/11 64-bit
- Python：建议 3.10+（与 PySide6/生态更匹配）
- 可选 GPU：NVIDIA CUDA（用于 onnxruntime-gpu 或 CTranslate2 GPU）

### 5.2 GPU 可选加速说明

- 如果 OCR 走 ONNXRuntime GPU：需要安装 CUDA/cuDNN 并使用对应的 onnxruntime-gpu 包；ONNX Runtime 文档明确说明 GPU 包需要 CUDA 和 cuDNN。[ONNX Runtime+1](https://onnxruntime.ai/docs/install/?utm_source=chatgpt.com)
- 如果走 PaddleOCR GPU：Paddle 安装指南提到可自动处理 CUDA/cuDNN 安装（具体仍要按版本匹配实践）。[PaddlePaddle](https://www.paddlepaddle.org.cn/documentation/docs/en/install/index_en.html?utm_source=chatgpt.com)
- 如果翻译走 Argos：可通过环境变量让它把 device 类型传给 CTranslate2，从而启用 GPU。[GitHub](https://github.com/argosopentech/argos-translate)

**建议**：先做 CPU 版闭环；若性能不足再上 GPU（尤其是 OCR 部分）。

------

## 6. 打包与交付形态（Windows 可分发）

### 6.1 打包工具：PyInstaller

PyInstaller 官方说明可把 Python 应用及依赖打包成可运行包/单文件，并包含 Python 解释器，使用户无需安装 Python。[PyInstaller+1](https://www.pyinstaller.org/?utm_source=chatgpt.com)

**推荐交付方式：one-folder（文件夹分发）**

- 原因：OCR/翻译模型文件通常较大且需要外置管理，one-file 会导致首次启动解压慢、也不利于模型更新。
- 目录建议：
  - `app.exe`
  - `models/ocr/...`
  - `models/translate/...`
  - `config.json`
  - `licenses/THIRD_PARTY_NOTICES.txt`

### 6.2 模型管理

- OCR 模型：随 RapidOCR 的默认模型或你自选 ONNX 模型一起放在 `models/ocr/`
- 翻译模型：
  - Argos：随 `.argosmodel` 包放在 `models/translate/argos/`（或按 Argos 默认路径安装后复制）
  - CTranslate2：放 `models/translate/ct2/`，支持量化版本（int8）以减小体积、提升速度。[GitHub](https://github.com/OpenNMT/CTranslate2)

------

## 7. 许可与合规（建议在文案里明确写）

你这个项目会“打包分发第三方库+模型”，建议在方案里把许可风险先写清楚：

- DXcam：MIT license [GitHub](https://github.com/ra1nty/DXcam)
- RapidOCR：Apache-2.0；并注明 OCR 模型版权归属（Baidu）[GitHub](https://github.com/RapidAI/RapidOCR)
- PaddleOCR（如用）：Apache-2.0 [GitHub](https://github.com/PaddlePaddle/PaddleOCR)
- Argos Translate：MIT（且 README 提到双许可 MIT/CC0）[GitHub](https://github.com/argosopentech/argos-translate)
- CTranslate2：MIT [GitHub](https://github.com/OpenNMT/CTranslate2)
- OPUS-MT en→zh（Helsinki-NLP）：Hugging Face 页面标注 license: apache-2.0 [Hugging Face](https://huggingface.co/Helsinki-NLP/opus-mt-en-zh)
- UI 框架：
  - PySide6：Qt for Python 说明可用 LGPLv3/GPLv3/商业许可（建议按 LGPLv3 路线合规分发）[Qt Documentation+1](https://doc.qt.io/qtforpython-6/?utm_source=chatgpt.com)
  - PyQt5：GPLv3（闭源分发通常需商业许可）[PyPI+1](https://pypi.org/project/PyQt5/?utm_source=chatgpt.com)

另外，如果你考虑用 LibreTranslate 作为本地翻译服务：其仓库明确是 **AGPL-3.0**，对分发/商用会更敏感；嵌入式桌面软件一般不建议默认走这条路线。[GitHub](https://github.com/LibreTranslate/LibreTranslate)

------

## 8. 风险点与对应策略

1. **DPI 缩放导致 ROI 偏移**
   - 解决：进程 DPI Awareness 设置 + 获取真实像素坐标；并在 UI 选区时做一致的坐标系转换。
2. **全屏游戏/硬件加速窗口捕获黑屏**
   - 优先 DXcam（它强调对 Direct3D 独占全屏捕获支持）。[GitHub](https://github.com/ra1nty/DXcam)
   - 失败时降级到 mss 或提示用户切换无边框窗口模式。
3. **OCR 抖动导致翻译闪烁**
   - 解决：文本稳定器（相似度阈值、最小刷新间隔、缓存）
4. **翻译延迟导致体验差**
   - 解决：翻译与 OCR 解耦；翻译只在文本变化时触发；使用 CTranslate2 量化模型或启用 GPU。[GitHub+1](https://github.com/OpenNMT/CTranslate2)

------

## 9. 分阶段交付（不写时间，只写里程碑）

- **阶段 1：闭环 MVP**
  - ROI 选区
  - DXcam 截取 ROI
  - RapidOCR 输出英文文本
  - 在浮窗显示识别文本（先不翻译）
- **阶段 2：本地翻译接入**
  - Argos Translate 英→中模型
  - 翻译结果浮窗展示 + 复制按钮
- **阶段 3：体验优化**
  - 变化检测、去抖、缓存
  - 点击穿透叠加层 + 热键控制
  - 一键切换“字幕条/旁注模式”
- **阶段 4：分发打包**
  - PyInstaller one-folder
  - 模型目录与配置文件管理
  - Third-party notices/许可证文件整理 [PyInstaller+1](https://www.pyinstaller.org/?utm_source=chatgpt.com)

------

## 推荐的“默认落地组合”（一句话版）

**DXcam（采集） + RapidOCR-onnxruntime（OCR） + Argos Translate（翻译） + PySide6 透明置顶叠加（展示）**
 在 Windows 上工程阻力最小，先做成再逐步把翻译替换成 CTranslate2+更强模型。