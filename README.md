# 定格物理

**拍一道初中物理题，得到一段带配音的讲解视频。视频能停在任意一帧，看清这一刻的每个物理量。**

第九届传智杯 AI Web 网页开发挑战赛参赛作品 · 方向：教育与学习 / 多模态创意平台

- 在线演示：<https://dinggell.cn>（提交题目需要邀请码，见提交材料）
- 首页有四道现成的例题（滑轮组、浮力、斜面、杠杆），不用邀请码就能直接看

## 它解决什么问题

初中物理的难点常常在“过程”：滑轮组提升时绳端走了多远、物体浸入水中时浮力怎样变、杠杆转动时力臂怎样变。
课本和教辅只能给静态的图和最后的答案，学生看不到“过程中的某一刻”各个量是多少。

定格物理把一道题变成一段老师讲题式的动画：

1. **读题**：题目铺满画面朗读一遍，读到已知量就用手绘的圈、下划线、勾标出来；
2. **一问一问讲**：讲到哪一问，再把这一问拿出来读、划线；板书只写这一问，写完停一下，用板擦擦掉再讲下一问；
3. **物理过程会动**：物体上升、浸入、杠杆转动……需要时还会让某段过程重新动一遍；
4. **随时定格**：网页播放器里暂停在任何一帧，右边面板显示这一帧的全部物理量，点画面上的物体只看它的量；
5. **文字解析**：答案、已知量、每一步的算式，每一步配上视频里对应时刻的截图，点截图视频就跳过去。

## AI 怎么做这件事

```
拍照/文字 ──► ① 读图转写 ──► 用户核对 ──► ② 独立解题 ──► ③ 检索示例 + 写场景代码
                (多模态)        (人在回路)    (推理模型)       (RAG + 代码生成)
                                                                    │
     ⑥ 网页播放器 ◄── ⑤ 配音 + 渲染 ◄── ④ 静态检查 → 容器内预演 → 答案互校 ──┘
      (逐帧读数)       (TTS + Manim)        不通过就把问题交回模型修改（最多 4 轮）
```

| 环节 | 做法 | 用到的 AI |
|---|---|---|
| ① 读图 | 支持一道题分几张照片拍（题目和题图分开），转写成文字和题图要点，交给用户核对后再继续 | DeepSeek 多模态模型 |
| ② 解题 | 独立解出每一问，给出已知量、步骤、答案和易错点；选择题给出选哪项和理由 | DeepSeek（高推理强度） |
| ③ 写代码 | 按题型从示例库检索最接近的示例，连同零件手册交给模型，写出调用固定零件库的场景代码 | DeepSeek（代码生成） |
| ④ 检查 | AST 静态检查（禁止危险调用）→ Docker 隔离容器里预演布局（文字重叠、出界、压线）→ 代码算出的答案和独立解答逐项比对 | 检查结果作为反馈交回模型自我修正 |
| ⑤ 配音渲染 | 旁白整段合成，按逐字时间戳切回每句；数字先转成中文读法；Manim 只渲染画面真正变化的帧 | Breeze Blue 语音合成 |
| ⑥ 播放 | 视频和面板读同一份逐帧数据，暂停时读数和画面严格一致 | — |

几个关键设计：

- **固定零件 + 模型写代码**：滑轮组、杠杆、斜面、烧杯、弹簧测力计、电路元件等画法写死在零件库里（`render/physkit`），模型只决定用哪些零件、放在哪、和哪个物理量绑定。画面稳定，又能覆盖没见过的题。
- **两路独立计算互相核对**：解题模型和场景代码各算一遍答案，不一致就不发布，按题目要求的位数比较。
- **安全可控**：模型写的代码只在断网、只读、无特权、限内存限进程的 Docker 容器里运行（`service/runner.py`，`python -m service.isolation_test` 可验证）。
- **缺零件会被记下来**：模型遇到零件库没有的东西时先用基础零件拼，并写下需求，维护者据此补零件。

## 测试结果

用 23 道 2024 年山东各市中考物理真题（德州、青岛、聊城、威海、烟台、枣庄、泰安、淄博、济宁、临沂、滨州、济南）做回归测试：

- 解题全部正确，包括选择题、填空题、读图像题；
- 23 道全部生成通过，16 道第一次就写对，平均写代码约 100 秒；
- 测试脚本在 `.dev/bench_effort`（不进仓库，含题目原文）。

## 技术架构

| 部分 | 技术 | 目录 |
|---|---|---|
| 网页 | Next.js 16（App Router）、React 19、TypeScript | `web/` |
| 接口 | FastAPI，任务排队、邀请码限流、结果分发 | `service/api.py` |
| 生成流水线 | 读图、解题、写代码、检查、配音、渲染 | `service/pipeline.py` |
| 提示词与示例检索 | 零件手册由代码文档字符串自动生成，示例按题型关键词检索 | `service/prompts.py`、`service/examples.py` |
| 渲染 | Manim Community 0.22，零件库 physkit，手绘标注 | `render/physkit/` |
| 隔离运行 | Docker 渲染镜像，断网只读 | `render/Dockerfile`、`service/runner.py` |
| 部署 | 香港云服务器跑网页和接口（Caddy + systemd）；笔记本 worker 领任务，调用模型并在容器里渲染后传回 | `deploy/`、`scripts/` |

```
dingge-physics/
├── web/                 网页（首页、讲解页、播放器、文字解析、反馈）
├── service/             接口、生成流水线、DeepSeek 与配音客户端、worker
├── render/
│   ├── physkit/         零件库、时间线、舞台、读题卡片、手绘标注
│   ├── examples/        按题型分类的示例场景（模型写代码时参考）
│   ├── CATALOG.md       零件手册（由代码生成，交给模型）
│   └── Dockerfile       渲染镜像
├── deploy/              服务器的 systemd、Caddy 配置和安装脚本
├── scripts/             开发、部署、worker、字体、例题发布脚本
└── spike/               最早的可行性原型（保留作开发记录）
```

## 安装运行

需要：Python 3.12、Node.js 20+、Docker Desktop（Windows）或 Docker Engine（Linux），以及 DeepSeek 和 Breeze Blue 的 API 密钥。

```bash
# 1. Python 依赖（生成流水线和接口）
python -m venv .venv
.venv/Scripts/pip install -r service/requirements.txt      # Linux/macOS 用 .venv/bin/pip

# 2. 网页依赖
cd web && npm install && cd ..

# 3. 渲染镜像（Manim 和零件库都在里面，模型写的代码只在这里运行）
docker build -t physics-renderer:0.1 render

# 4. 配置：照 .env.example 设置环境变量，密钥只放在环境变量里
#    CHUANZHI_DEEPSEEK_API_KEY、CHUANZHI_BREEZE_API_KEY 必填

# 5. 本机启动接口、网页和 worker（Windows），打开 http://127.0.0.1:3100
powershell -File scripts/dev.ps1
#    停止：powershell -File scripts/stop.ps1
```

验证隔离容器确实生效：

```bash
.venv/Scripts/python -m service.isolation_test
```

检查一份场景代码并渲染成视频（不配音）：

```bash
.venv/Scripts/python scripts/check_scene.py render/examples/pulley_n3.py --render
```

线上部署：服务器只需要 `service/requirements-server.txt`，`bash scripts/deploy.sh` 构建网页并安装到服务器；笔记本上运行 `scripts/worker.ps1` 领任务。

## 团队信息

- 参赛组别：A 组
- 学校：中国海洋大学
- 队员：陈璐豪、闫文瀚、高郡遥

## 致谢

- [Manim Community](https://www.manim.community/)（MIT）：动画渲染
- [rough-notation](https://github.com/rough-stuff/rough-notation)（MIT）：手绘标注的画法思路，我们在 Manim 里重新实现
- [Noto Serif SC](https://fonts.google.com/noto/specimen/Noto+Serif+SC)（SIL OFL 1.1）：网页标题字体
- DeepSeek、Breeze Blue：大模型与语音合成服务
