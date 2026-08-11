# RealtimeAcc 技术要求文档（夜间自动化执行版）

> 版本：v1.0 · 2026-08-12 · 状态：**待执行**
> 本文档由前一会话调研/确认后定稿；本会话仅做初始化（文档+权限+git）。**正式开发在下一轮全新会话开始**（建议清空上下文），执行方式见 §12 / §16。

---

## 1. 项目概述

- 目标：Phigros 推分实时辅助。iPad 屏幕实时镜像到 PC → CV+OCR 统计判定（Perfect/Good/Bad/Miss）→ 实时计算当前 ACC、已扣 ACC、最大可达 ACC → 与"推荐推分 ACC"目标比对 → **已不可能达到目标时 HUD 变红提示重开**。
- 主设备：iPad（AirPlay 免费接收器镜像）；备选：摄像头、本地视频回放（离线调优）。
- 技术栈：Python 3.12 + OpenCV + pytesseract（Tesseract 5，winget 安装）+ mss + pywin32 + tkinter；`requests` 联动本地 lilith 后端（`http://127.0.0.1:3930`）。
- **零侵入**：不改 `lilith-xtower` / `Next-Phi-Backend` 源码，仅以 HTTP 契约读取其已有接口（§6）。

## 2. 判定数学（口径已确认，勿改动）

| 判定 | ACC 贡献 | 备注 |
|---|---|---|
| Perfect | 100% | 连击+1 |
| Good | 65% | 连击+1 |
| Bad | 0% | 连击清零 |
| Miss | 0% | 连击清零 |

- `ACC = (P + 0.65×G) / N × 100`
- `已扣ACC = (0.35×G + B + M) / N × 100`（已放弃的 ACC 点数；Bad 与 Miss 扣分等效）
- `最大可达ACC = 100 − 已扣ACC × 100`（后续全部 Perfect）
- **判红条件（目标为具体值）**：`最大可达ACC < 目标ACC`
- **判红特例（目标=100，需 Phi）**：出现任意 Good/Bad/Miss 立即红，无需 N
- **N 未知**：HUD 显示灰"推算中"，不判红（需 Phi 特例除外）。N 来源优先级见 §5
- N = 总谱面键数（物量）

## 3. 系统架构与数据流

```
iPad ──AirPlay(同WiFi)──► 1PhoneMirror / uxplay  PC窗口
  │ capture.py：win32gui 找窗 + mss 按校准矩形抓帧（≥15fps）
  ├─► 判定区ROI ──► judge.py：帧差触发 + 350ms去抖 + Tesseract 分类
  ├─► 分数区ROI ──► score OCR（仅用于 N 自动估算的增量）
  └─► acc.py 状态机 ──► hud.py：当前ACC/已扣/最大可达/N/目标/红绿
target.py：POST 后端 /api/v2/save?calculate_rks=true
      └─► 解析 push_acc + push_acc_hint ──► 选歌器 ──► 目标ACC
```

延迟预期：镜像 100-300ms + OCR 50-150ms，计数滞后可接受（非触控用途）。

## 4. 模块规格

### 4.1 capture.py
- `airplay`：`win32gui.EnumWindows` + 标题关键词匹配（1PhoneMirror/uxplay/ffplay/AirPlay…），匹配失败读 `config.capture.window_title` 手填；用用户一次校准的窗口内矩形 `mss` 抓取；窗口消失每 2s 轮询重连。
- `video`：`cv2.VideoCapture(path)` 逐帧（离线调优模式，支持暂停/步进）。
- `camera`：`cv2.VideoCapture(index)` 兜底。
- 目标帧率 ≥15fps，受 OCR 预算约束；帧差判定敏感度按 100ms 粒度。

### 4.2 calib.py
- 首次运行（或 config 无 ROI）时显示定格帧，鼠标框选 3 个 ROI：**判定文字区 / 分数区 / 结算页区** → 写入 config.json 持久化。

### 4.3 judge.py
- 每帧取判定 ROI 灰度，`|Δ|` 均值超 `diff_threshold` → 触发判定事件；距上次触发 ≥ `debounce_ms(350)` 才接受新事件（连打/长押/多押合并防重复）。
- 分类：裁 ROI → ×2 放大 → CLAHE → OTSU 二值 → `pytesseract.image_to_string(psm=7, allowlist=PerfectGoodBadMiss)` → 匹配（exact / startswith / contains）→ 置信 < `conf_min(0.55)` 丢弃但记日志（供调参）。预留模板匹配兜底接口。

### 4.4 acc.py（纯函数状态机，独立可单测）
- 计数 P/G/B/M；输出：`current_acc`、`lost_acc`、`max_acc`、`n_status(unknown|locked|manual)`、`hits`。
- N 自动估算：监听分数 OCR 的增量 Δ —
  - 无断连期间 Perfect 增量 ≈ `1,000,000/N`；断连后（Bad/Miss 刚发生且未恢复最大连击）增量 ≈ `900,000/N`；
  - 候选取整后**连续 ≥3 次一致即锁定**（`locked`）；
  - 失败不阻塞计数，仅 N 延迟（§13）。
- N 优先级：`info/notes.csv`（§5）> 手动覆写 `config.rks.n_manual` > 每歌缓存 `n_cache[songId_diff]` > 自动估算。

### 4.5 target.py（目标联动，接口契约见 §6）
- 从 `.secrets/session_token.txt` 读 token；POST `{backend_base}/api/v2/save?calculate_rks=true`，body `{"sessionToken": ...}`；401 → 提示 token 失效；网络失败指数退避重试 3 次；结果缓存。
- `push_acc_hint` 映射：
  - `target_acc` → 目标 = `push_acc`（API 精确 3 位小数，**原样使用**）
  - `phi_only` → 目标 = 100（`phiGoal` 标记，走 §2 特例）
  - `unreachable` → 状态"当前推分线无法推分"（HUD 常显红）
  - `already_phi` → 状态"已满 ACC"（中性提示）
- **用户规则（不可违背）**：仅当目标来自"网页显示值 / 手动输入（2 位小数）"时目标 = 值 + 0.01；API 精确值直接使用；手动输入口一律按 2 位小数规则处理。
- 选歌器：只列出有目标/状态的谱面（songId+难度+目标），HUD 下拉，记住上次选择（`config.song_cache`）。songId 与后端 `game_record` 键一致。

### 4.6 hud.py
- tkinter 置顶无边框可拖动窗；字段：歌名/难度、目标（或"需Phi"/"—"）、当前ACC、已扣ACC、最大可达ACC、N状态、P·G·B·M、状态行。
- 配色：白/绿 = 可继续；**红 = 建议重开**；灰 = 数据不足（N 未知等）。
- 变红瞬间蜂鸣一次（`winsound.Beep`，可配置关闭）。

### 4.7 main.py
- 载荷配置 → 校准（如需）→ 初始化各模块 → 主循环（抓帧→判定→计分→渲染→UI 事件）；`--video/--camera/--airplay` 三模式。
- 结束哨兵（视频播完/用户关窗/手动按键）→ 输出本局统计 JSON 到 `runs/`（供对账，§8）。

### 4.8 config.json schema（先例）
```json
{
  "capture": { "mode": "airplay", "window_title": "", "video_path": "", "camera_index": 0 },
  "roi": { "judge": [0,0,0,0], "score": [0,0,0,0], "result": [0,0,0,0] },
  "judge": { "debounce_ms": 350, "diff_threshold": 18, "conf_min": 0.55 },
  "target": { "backend_base": "http://127.0.0.1:3930" },
  "hud": { "font_size": 20, "topmost": true, "beep_on_red": true },
  "rks": { "n_manual": null, "n_cache": {} },
  "song_cache": { "last_song_id": null }
}
```

## 5. 物量数据（note count，N）

- 载体：`info/notes.csv`，表头 `song_id,difficulty,note_count`（song_id 与后端一致；difficulty: EZ/HD/IN/AT）。
- 来源两条路径并行：
  1. **web 调研子 agent（W4）**：搜 Phigros 全曲物量数据源（wiki/开源数据集），能确认可靠 → 生成 `info/notes.csv`；
  2. **用户醒来后补文件**：解析器宽容接受 CSV/JSON，键支持 song_id 或歌名、难度别名，无法解析的行记日志跳过，不中断。
- 查不到可靠源 → 留模板文件（表头+示例行），最终报告写明期望格式。
- 物量已知时进歌即可判红（无需等 N 估算）。

## 6. 目标联动后端契约（固定，勿改）

- `POST {backend_base}/api/v2/save?calculate_rks=true`
- Body：`{"sessionToken": "<TapTap sessionToken>"}`（即登录 lilith 网页用的同款 token）
- 响应定位：`save.game_record || save.gameRecord` → `{songId: [ {difficulty, accuracy, score, chart_constant, push_acc?, push_acc_hint?: {type, acc?}} ]}`
- hint.type：`target_acc | phi_only | unreachable | already_phi`
- token 未就绪时：`target.py` 以 mock 响应跑通全链路（标注待填），不阻塞 v0.4。

## 7. 后端随仓（正式版 v1.0 前置）

- `backend/` 收录 `Next-Phi-Backend` 运行 `/save?calculate_rks=true` 的最小子集（**本地快照拷贝，非 submodule**）：
  - `Cargo.toml`、`crates/phi-save-codec/`、`src/`、`resources/info/`（含 difficulty.csv）、`config.example.toml`
  - 排除：`target/`、`sdk/`、`tests/`、`examples/`、`.git/`、`backend.log`、`config.toml`（本地私密配置）
- `scripts/start-backend.ps1`：PATH 注入 `C:\msys64\mingw64\bin` → `cargo +stable-x86_64-pc-windows-gnu build --release` → 从 `config.example.toml` 派生本地 `config.toml`（`illustration_repo_auto_sync = false` 等）→ 启动 `:3930`（幂等，先查端口占用）。
- 同步策略写入 README：快照式，手动同步，勿与上游混为一谈。

## 8. 离线验证与验收门槛

- 输入：`sample.mp4`（含判定过程 + 结尾结算页官方 P/G/B/M 计数）。
- 流程：`--video` 回放 → 判定计数 → 结算区 OCR 官方计数 → 对账写入 `runs/`。
- **门槛**（不达则不进入 v0.3）：
  - P/G/B/M 各自与结算页一致率 ≥ 95%，**零重复计数**；
  - 结算 ACC 与累计 ACC 偏差 < 0.1%；
  - N：估算收敛值合理（`判定数 ≤ N`，与增量一致性检查）。
- 结算页 OCR 失败 → 跳过对账仅报告差异。

## 9. Git 工作流

- **通道（已解决）**：直连 HTTPS 被网络 reset（不可用）；**SSH 端口 22 已认证成功**（`~/.ssh/config` 已配 `id_rsa_github`，`ssh -T git@github.com` → `Hi zhuhaoxiangAndy!`）。remote origin = `git@github.com:zhuhaoxiangAndy/RealTimeAccPhigros.git`。
- 分支：`main`（本地 master 已重命名并推送首个提交：本文档 + .gitignore + opencode.json）。
- 提交规范：中文原子提交；**每完成一个工单/里程碑验证通过即 push 一次**；里程碑打 tag：`v0.1 骨架` → `v0.2 离线计数` → `v0.3 实时+HUD` → `v0.4 目标联动+物量` → `v0.5 后端随仓` → `v1.0 完结`。
- 回滚：`git reset --hard <tag>` 或 `git revert`（失败重来以最近 tag 为锚）。
- 备选通道（仅 fetch）：`https://ghfast.top/https://github.com/...`（已验证 ls-remote 可用；push 不用镜像）。
- `.gitignore`：`.secrets/`、`config.local.json`、`.venv/`、`__pycache__/`、`*.pyc`、`runs/`、`.trash/`、`sample.mp4`、`backend/target/`、`backend/config.toml`。
- 敏感信息：token 只进 `.secrets/`（不入库）；文档 §15 占位的 token 由执行者在读取后**从 md 抹除再提交**。

## 10. 会话权限与操作纪律（本会话已配置 opencode.json，重启生效）

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "question": "deny",
    "read": "allow",
    "webfetch": "allow",
    "websearch": "allow",
    "todowrite": "allow",
    "edit": { "*": "deny", "D:/Documents/Phi/RealtimeAcc/**": "allow" },
    "glob": { "*": "deny", "D:/Documents/Phi/RealtimeAcc/**": "allow" },
    "grep": { "*": "deny", "D:/Documents/Phi/RealtimeAcc/**": "allow" },
    "list": { "*": "deny", "D:/Documents/Phi/RealtimeAcc/**": "allow" },
    "bash": { "*": "allow", "rm *": "deny", "rm": "deny", "git rm *": "deny",
              "Remove-Item": "deny", "Remove-Item *": "deny", "del *": "deny",
              "erase *": "deny", "rmdir *": "deny", "rd *": "deny" },
    "external_directory": { "*": "allow" }
  }
}
```

- **纪律（无论配置是否拦截都必须遵守）**：
  - `question` 已 deny → 执行期禁止提问/征求确认，一切决策自主、记录进最终报告；
  - **禁止一切 rm**（含 `Remove-Item/del/erase/rmdir/rd/git rm`）；需要清理的文件一律 `Move-Item` 到仓库内 `.trash/`；
  - `glob/grep/list/edit` 只允许 RealtimeAcc 仓库内；外部目录（如 `../lilith-xtower`、`../Next-Phi-Backend`）**只读可用、禁止写入、禁止在其中执行 bash**（读取参考契约/做快照拷贝来源时只读）；
  - 子 agent 并发 **≤3**，禁止并行 4 个及以上。

## 11. 子 agent 计划（计划分布模式）

调度规则：主 agent 负责编排/集成/验证/git；子 agent 只做独立工单（输入文件→输出文件契约），互不读写对方产物；验收由主 agent 执行（跑测试/对账），不信任子 agent 自报完成。

| 工单 | 子 agent 角色 | 输入 | 输出 | 验收 |
|---|---|---|---|---|
| W1 | judge-tuner | sample.mp4 抽样帧 + 手动标注真值表 | 判定参数建议 + 预处理参数 | 主 agent 用 acc/judge 管线对账 |
| W2 | acc-engine | 本文 §2/§4.4/§5 | `acc.py` + `tests/test_acc.py`（公式/临界/+0.01/phi_only/N未知分支） | `pytest` 全绿 |
| W3 | target-client | 本文 §6 契约 + mock 样例 JSON | `target.py`（含 +0.01 规则、hint 映射、token 缺失降级） | mock 用例通过；真接口就绪后复核 |
| W4 | web-research（可后台） | 无（联网） | `info/notes.csv` 或"无可靠源"结论 | 抽查来源可信度；无源则留模板 |
| W5 | docs | 全部 | README.md（安装/校准/使用）、scripts/setup.ps1 | 文档与实装命令一致性抽查 |

并行组合（上限 3）：W2+W3+W4 首轮并行；W1 依赖帧采样可与 W2 并行；W5 末轮。失败 → 子 agent 返回原因，主 agent 裁决（降级方案见 §13）或回滚到最近 tag。

## 12. 执行顺序与里程碑（下一会话按此执行）

1. **开场**：读本文档 → `git pull` → 检查 `.secrets/session_token.txt` 与 §15 占位（若有则迁移并抹除 md 中的值）→ 建 venv、装依赖（requirements.txt：opencv-python、mss、pytesseract、requests、pywin32、pytest）。
2. **v0.1 骨架**：工程结构、config/calib 雏形、git 基础提交 → push + tag `v0.1`。
3. **v0.2 离线计数**：judge+acc+video 回放跑通，`sample.mp4` 对账达 §8 门槛 → push + tag `v0.2`。
4. **v0.3 实时链路**：winget 装 Tesseract(UB-Mannheim) 与接收器(1PhoneMirror，备选 uxplay-windows) → airplay 抓窗 + HUD 红绿 → push + tag `v0.3`。
5. **v0.4 目标联动+物量**：target.py 接本地后端（token 就绪连真接口，否则 mock）、选歌器、phi_only 特例、notes.csv 接入 → push + tag `v0.4`。
6. **v0.5 后端随仓**：§7 快照拷贝 + start-backend.ps1 可编译可启动 → push + tag `v0.5`。
7. **v1.0 完结**：README/setup.ps1 补齐、全量自检（单测+离线对账复跑）、最终执行总结报告（全部自主决策清单、遗留项：如 token 待填/物量缺失/对账跳过）→ push + tag `v1.0`。

## 13. 风险与缓解

| 风险 | 缓解 |
|---|---|
| GitHub 直连被 reset | 已解决：SSH:22 认证通过；ghfast 镜像兜底 fetch |
| 判定花体字 OCR 误判 | 放大/二值/白名单/置信调参（W1）；预留模板匹配兜底 |
| 分数区 OCR 不稳 | 只取增量符号/千分位；失败仅延迟 N，不阻塞计数 |
| N 长期未知 | notes.csv（W4/用户文件）优先；HUD 灰态不判红（除需 Phi） |
| 接收器安装失败/启动挂起 | 备选 uxplay-windows；再失败→摄像头兜底或 v0.3 延期并在报告说明 |
| AirPlay 窗口标题不稳定 | 关键词多候选 + 手填 title + 2s 轮询重连 |
| 镜像延迟 100-300ms | 计数滞后可接受，不参与触控 |
| TAP_SESSION_TOKEN 缺失 | target.py mock 全链路自测，报告标注"待用户填 token" |
| 后端不在运行/端口占用 | v0.4 提示检测 3930 存活；v0.5 后可用 start-backend.ps1 自起 |
| 物量无可靠源 | 留模板 + 宽容解析器，用户醒后补文件即生效 |

## 14. 交付清单（v1.0）

- `docs/TECH_REQ.md`（本文）、`README.md`、`requirements.txt`、`scripts/setup.ps1`、`scripts/start-backend.ps1`
- 源码：`capture.py` `calib.py` `judge.py` `acc.py` `target.py` `hud.py` `main.py`、`tests/test_acc.py`
- 数据：`info/notes.csv`（或模板）、`config.json`（示例）、`.secrets/`（不入库）
- 产物：`runs/` 离线对账报告、最终执行总结报告
- 远端：GitHub `RealTimeAccPhigros` main 分支全量提交 + 里程碑 tags

## 15. 用户凭据占位（由用户填入）

> GIT：无需 token，SSH 已配置（id_rsa_github，端口 22 已验证）。
> 执行者注意：读取本节后把 token 迁移到 `.secrets/session_token.txt`（gitignore），并**抹除本节中的 token 值后**提交。

```
TAP_SESSION_TOKEN = <用户在此粘贴 TapTap sessionToken，登录 lilith 网页同款>
```

## 16. 下一会话开场指导

1. 新开 session（建议，见会话结束说明）；工作目录 = `D:\Documents\Phi\RealtimeAcc`；opencode.json 权限在重启后生效（question=deny 等）。
2. 先读本文档 → `git pull --rebase`（远端可能已有本会话首推的初始化提交）。
3. 处理 §15 凭据 → 建 `.secrets/` → 执行 §12。