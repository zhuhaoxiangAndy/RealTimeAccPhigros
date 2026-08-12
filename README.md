# RealtimeAcc — Phigros 推分实时辅助

[English](README-en.md) · [中文](README.md)

> 对 iPad/录像中的 Phigros 画面进行 CV+OCR 判定统计：实时计算当前 ACC、最大可达 ACC，
> 与目标 ACC 比对，**已不可能达成目标时标红提示重开**。

## 特性

- 离线对账：对本地录像 `sample.mp4` 跑通全流程，判定计数与结算页一致率 P 95.1% / G 97.1%
- 实时模式：mss 抓取屏幕 → 分数 OCR → 判定增量分解 → 实时 ACC 与判红（`run`）
- 回放自测：`run --demo` 按 1:1 节奏回放录像验证实时链路
- 配置化：全部参数集中在 `config.example.toml`，复制为 `config.toml` 即可覆盖
- 测试：`pytest` 18 项覆盖 ACC 数学、增量分解、窗口锚定

## 安装

```powershell
# 1. Python 3.12（需求已在 .venv 安装）
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 2. Tesseract 5（OCR 引擎，UB-Mannheim 构建）
winget install UB-Mannheim.TesseractOCR
# 将 C:\Program Files\Tesseract-OCR 加入 PATH
```

## 使用

```powershell
# 离线计数（sample.mp4 对账用窗口来自 config）
python main.py video sample.mp4

# 与结算页基准对账，报告写入 runs\report_*.md
python reconcile.py sample.mp4

# 实时链路自测（1:1 回放）
python main.py run --demo

# 实时屏幕判定（iPad 镜像窗口上点击/全屏）
python main.py run
```

`run` 每次命中判定会输出一行：`P 659 G 34 N 693 ACC 93.47% ... RED=False`，
`RED=True` 表示最大可达 ACC 已低于目标（§2 判红逻辑）。

## 配置（config.example.toml → 复制为 config.toml）

- `[video]`：离线窗口 `start/end`、采样步长
- `[box]`：分数区 / 结算页区的坐标（2360×1640 录制实测值）
- `[ocr]`：CLAHE 参数、二值阈值、psm、白名单
- `[judge.weights]`：判定权重（Perfect=1.0 / Good=0.65 / Bad=0 / Miss=0，勿改动）
- `[goal]`：目标 ACC（判红阈值）
- `[expect]`：对账用结算页基准 `p/g/b/m`

> 注：实现采用 TOML 形态；TECH_REQ §4.8 的 JSON schema 作为字段语义参考。

## 判定计数原理（离线/实时共用）

1. 右上角分数显示 7 位数字，按 `cfg.sample_step` 帧（0.2s@60fps）采样
2. OCR 管线：裁剪 → ×2 立方放大 → CLAHE(2.0) → 二值(100) → psm7 纯数字 → 滑窗提取合法 7 位串
3. 增量分解：每音符显示值落在 P:[1227,1365] / G:[798,935]（累计取整漂移），优先最大 P 解
4. 抖动鲁棒：负增量跳过不重置；失败增量保留上次锁定值；`--start/--end` 未指定时倒退锚定

## 里程碑与验收（对照 docs/TECH_REQ.md §12）

| 里程碑 | 结果 | 说明 |
|---|---|---|
| v0.1 骨架 | ✅ tag v0.1 | 8 模块 + config 示例，编译通过 |
| v0.2 离线计数 | ✅ tag v0.2 | P 95.1% / G 97.1%（阈≥95%）、零重复、18 pytest |
| v0.3 实时链路 | ⚠️ tag v0.3 | mss 实时 + demo 自测通过；AirPlay 接收器与 tkinter HUD 未装/未实现 |
| v0.4 目标联动 | ⚠️ tag v0.4 | Target.verdict 判红已接入实时循环；后端 HTTP 联动/选歌器/notes.csv 未实现 |
| v0.5 后端随仓 | ❌ tag 已占位 | backend/ 快照与 start-backend.ps1 未做（无本地 Next-Phi-Backend 副本） |
| v1.0 完结 | ✅ tag v1.0 | 双 README、setup.ps1、全量自检 |

## 已知限制与遗留项

1. **判定文字未显示**（录像设置关闭）：B/M 无法经分数增量区分，只能合并计数并以
   N 兜底；40 音符（约 5.5%）未能归因 → 对账 ACC 偏差 −4.73pp（目标 <0.1pp 未达，记录在案）
2. **结算明细页 OCR 不可靠**：半透明灰字样式，基准值来自结算页静态读数
3. **AirPlay 实物链**：iPad USB-C 有线连接已具备，接收器（1PhoneMirror/uxplay）安装与
   镜像实测待做；`capture.live_frames` 现为全屏抓取，窗口标题匹配（win32gui）未实现
4. **目标后端联动**：`.secrets/session_token.txt` 已就绪，POST 契约（§6）未实现，
   当前判红仅基于本地配置的 `goal.acc`
5. **物量数据**：`info/notes.csv` 仅模板，N 依赖估算兜底

## 目录结构

```
config.py / capture.py / calib.py / judge.py / acc.py
target.py / hud.py(main.py)      # 模块源码
main.py / reconcile.py           # CLI：video/raw/run、对账
config.example.toml              # 配置示例
tests/test_judge.py              # 18 项 pytest
runs/                            # 对账报告产物（gitignore）
info/notes.csv                   # 物量模板（宽容解析待实现）
docs/TECH_REQ.md                 # 技术要求文档（口径依据）
docs/V1.0_SUMMARY.md             # 执行总结报告
scripts/setup.ps1                # 一键环境安装
```

## 许可与说明

个人学习项目；判定数学口径见 docs/TECH_REQ.md §2（勿改动）；详细偏差与根因见
docs/V1.0_SUMMARY.md §5-§6。