# 定格物理：给 Claude 的说明

传智杯参赛作品：拍题或输入初中物理题，DeepSeek 解题并按零件库写 Manim 代码，生成可暂停看物理量的讲解视频。
网页和 API 在香港服务器 https://dinggell.cn，任务由这台笔记本领取（`scripts/worker.ps1`），模型调用和渲染都在笔记本上，生成的代码只在 Docker 里跑。

## 每次开始先看：零件库待处理

DeepSeek 碰到零件库没有的东西时，会先用基础零件拼，并在代码开头写 `# 缺少零件: 名称；用途；代替`。
笔记本上的 worker 会把这些需求和 UNSUPPORTED 的原因记到 `.dev/requests/`，汇总在 **`.dev/requests/待处理.md`**（按出现次数排）。
还没有示例的题型第一次做成功时，代码会存成候选：`.dev/requests/candidates/`。

用户打开新会话时，先读 `待处理.md`，告诉用户有哪些待做，问要不要做。做一种零件的步骤：

1. 看需求记录里 DeepSeek 拼出来的代码（`.dev/requests/<任务号>.py`），了解它想画什么。
2. 在 `render/physkit/parts.py` 里写零件：继承 Part，坐标和文字都能接受函数 `f -> 值`，`edges()` 和文字位置要能被 Stage 的布局检查用到。写好后在 `render/physkit/__init__.py` 的 `__all__` 里导出，文档字符串会进手册，要写清参数和用法。
3. 用这个零件写一个这类题的示例，放进 `render/examples/`，并在 `render/examples/index.json` 的 examples 里登记题型；题型或关键词不够的，同时改 categories。每个题型一两个示例就够，不用每道题都放。
4. 重新生成手册：在 `render/` 下运行 `../.venv/Scripts/python -m physkit.catalog > CATALOG.md`。
5. 检查示例：`.venv/Scripts/python scripts/check_scene.py render/examples/<文件>.py --render`，看视频截图确认画面。
6. physkit 改了要重建渲染镜像（`docker build -t physics-renderer:0.1 render`），再重启 worker。
   worker 由开机计划任务「dingge-worker」通过 `scripts/worker-service.ps1` 在后台运行，退出后 10 秒自动重启，日志在 `.dev/worker-service.log`。
   重启的做法是结束它下面的 `python -m service.laptop_worker` 进程（先确认服务器上没有正在做的题），不要再另开 `scripts/worker.ps1`，否则会有两个 worker 抢任务。
7. 把做完的零件的关键词加进 `.dev/requests/已处理.json`（JSON 数组，比如 "杠杆"），名字里含这个词的需求就不再列。
8. 候选示例要审核后再手动放进示例库，不要原样照搬，也不要自动加。

## 界面

- 界面风格是用户 2026-11-06 选定的设计 A「取景框」：纸面加和视频同色的深色台面，取景框四角是贯穿全站的图形。设计稿在 `.dev/design/a`，样式都在 `web/app/globals.css`。
- 标题用的宋体是从 Noto Serif SC 裁出来的小字体（`web/public/fonts`）。改了用宋体的标题，把新字加进 `web/fonts/serif-text.txt`，再运行 `python scripts/build_fonts.py`（用装了 fontTools 的 Python，比如 `D:\python\python.exe`）。
- 首页例题：代码是 `render/examples` 里的示例，解析写在 `render/examples/showcase.json`。`python scripts/publish_examples.py` 提交到线上，把打印的任务号填进 `web/lib/examples.ts` 再部署。示例代码改了，任务号也会变，要重新提交。

## 约定

- API 密钥只在 Windows 用户环境变量 `CHUANZHI_DEEPSEEK_API_KEY`、`CHUANZHI_BREEZE_API_KEY` 里，专用于本项目，不能写进任何文件。
- 服务器只用 SSH 密钥 `~/.ssh/dingge_server` 以 ubuntu 登录，不用密码。部署：`bash scripts/deploy.sh`。
- `.dev/` 里有评委提交的题目和令牌，不进仓库。
- 用户说提交时才 commit / push。装软件或改系统设置先问。
- 数字绝对值大于 10000 或小于 0.001 用科学计数法；字幕显示符号形式，配音读中文。
