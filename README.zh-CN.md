# showcase-progress

**一条 AI 编不出来的进度条。**

[![test](https://github.com/panzero666/showcase-progress/actions/workflows/test.yml/badge.svg)](https://github.com/panzero666/showcase-progress/actions/workflows/test.yml)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![deps](https://img.shields.io/badge/dependencies-none-brightgreen)
![license](https://img.shields.io/badge/license-MIT-green)

[English](README.md)

<p align="center"><img src="assets/demo.svg" alt="showcase-progress 演示" width="820"></p>

再看一眼上面的演示：Q2 做完之后，**剩余时间反而变多了**（4h10m → 4h16m）。
Q1、Q2 都比预估慢，脚本就不再相信原计划，按实际速度把剩下的重新算了一遍。
换成一般的 AI 汇报，这时候它会说"已完成 35%，快好了"。

## 问题在哪

问 AI Agent 做到哪了，你得到的是一种感觉，而不是一个数字：

- "完成 70%"——按什么算的？
- 把活拆成 20 个小步骤，先做容易的几个，进度立刻 50%。
- "再几分钟就好"——说了一个小时。
- 文件建好了就算这步完成，那它能跑吗？

## 这个 skill 做什么

showcase-progress 是一个 [Agent Skill](https://agentskills.io)：一份 `SKILL.md`
加一个零依赖的 Python 脚本。Agent 负责规划，脚本负责记账：

1. **进度按预计耗时加权，不按步骤个数。**
   `进度 = 已完成子任务的预计耗时 / 全部子任务的预计耗时`。拆得再碎也虚增不了。
2. **"进行中"记 0 分。** 只有 `done` 才算数。唯一的例外是真的数得出来
   （`--count 3/6`，已迁移 3 个接口）——数出来的是证据，估出来的"60%"不是。
3. **剩余时间会自己修正。** 记下已完成子任务的实际耗时（`--took 40m`）；
   有两个以上真实样本、覆盖计划 20% 以上、且速度偏差超过 15% 时，
   剩余时间按实际速度重算，并标注"按当前速度"。
4. **完成要有证据。** 子任务可以写验收条件 `done_when`；
   标了完成却没给证据的，`check` 会指出来。
5. **什么都不会丢。** 账本是项目里的一个 JSON 文件。关掉会话、明天回来，
   `render` 一下接着干。`replan` 改计划时保留已完成的工作，并记下为什么改。

## 安装

skill 就是一个文件夹，放到你的 Agent 读 skill 的地方即可。

| Agent | 位置 | 状态 |
|---|---|---|
| **Claude Code** | `~/.claude/skills/showcase-progress`（或仓库里的 `.claude/skills/`） | ✅ 已在真实多步任务上实测 |
| **Codex**（CLI / IDE / 桌面版） | `~/.agents/skills/showcase-progress`（或仓库里的 `.agents/skills/`） | ☑️ 已按官方文档核对目录结构 |
| **Gemini CLI** | `~/.agents/skills/` 或 `~/.gemini/skills/` | ⚪ 符合规范，未实测 |
| **OpenClaw** | `~/.agents/skills/`，或 `openclaw skills install git:panzero666/showcase-progress` | ⚪ 符合规范，未实测 |
| **其他支持 Agent Skills 的工具** | 各自的 skills 目录 | ⚪ 符合规范，未实测 |
| **ChatGPT / DeepSeek / Gemini 网页版 / Kimi / 豆包……** | 把 [`PROMPT.zh-CN.md`](PROMPT.zh-CN.md) 贴进自定义指令 | 📝 纯提示词版，数字是估算 |

**macOS / Linux**

```bash
git clone https://github.com/panzero666/showcase-progress.git
cd showcase-progress && ./install.sh          # 复制到 ~/.claude/skills 和 ~/.agents/skills
```

**Windows（PowerShell）**

```powershell
git clone https://github.com/panzero666/showcase-progress.git
cd showcase-progress; .\install.ps1
```

也可以手动复制文件夹。只需要 `PATH` 上有 Python 3.8+，别的都不要。

在标着"未实测"的 Agent 上试过了？[提个 issue](https://github.com/panzero666/showcase-progress/issues)
说说结果，这是现在最有用的贡献。

## 怎么用

不用点名。给 Agent 一个要花上一阵子的活——"给应用加上找回密码"、"把这 40 张表迁过去"、
"写季度报告"——或者问一句"这还要多久"。Agent 会：

1. 把活拆成 5–9 个子任务，诚实地估耗时；
2. 建账本，贴出起始进度条；
3. 每完成一个子任务贴一行进度；
4. 最后给一张"预计 / 实际"对照表。

也可以直接调用：Claude Code 里 `/showcase-progress`，Codex 里 `$showcase-progress`。

输出语言跟随任务标题：标题是中文就输出中文。也可以用 `--lang zh` 或环境变量 `SP_LANG=zh` 指定。

<details>
<summary><b>脚本命令一览</b></summary>

```bash
python3 scripts/progress.py init --plan plan.json            # 建账本
python3 scripts/progress.py update "Q1=done" --took 40m --brief
python3 scripts/progress.py update "Q2=done" --evidence "curl -> 202" --brief
python3 scripts/progress.py update "Q3=doing" --count 3/6 --brief
python3 scripts/progress.py update "Q4=blocked(等权限)"
python3 scripts/progress.py update "Q3=doing" --est 2h30m    # 修正单个估时
python3 scripts/progress.py replan --plan v2.json --reason "拆开 Q4"
python3 scripts/progress.py render [--mode block|bar|live|next]
python3 scripts/progress.py check                            # 数字不可信时 exit 1
python3 scripts/progress.py export                           # progress.json + PROGRESS.md
python3 scripts/progress.py history                          # 回放每一步
```

耗时写法：`40s`、`30m`、`1h30m`、`1.5h`、`90`（分钟）、`45分钟`、`2小时`。

环境变量：`SP_STATE`（账本路径，默认 `.showcase-progress/state.json`）、
`SP_LANG`（`en` / `zh`）、`SP_ASCII=1`（老式控制台用 `#-` 代替 `■□`）。

</details>

## 常见问题

**为什么"进行中"算 0？**
因为几乎所有虚高的进度都出在这里。进度条一跳一跳地涨，这才是真实进度的样子。
数得出来的工作量（`--count`）是展示步骤内部进展的诚实办法。

**为什么不用三点估算（PERT）？**
让模型报乐观、最可能、悲观三个数，等于猜三遍，还显得比实际更精确。
一个诚实的估计，加上按实测速度修正，每做完一个子任务就更准一点。

**它能测出模型思考了多久吗？**
不能，也不会假装能。"已开工"是从建账本开始的钟表时间；每个子任务的真实耗时来自 `--took`。

**会在后台自动刷新吗？**
不会。Agent 没有常驻进程，所以进度条是在子任务边界贴出来的快照。
如果你的平台有定时器，可以让它去调用 `render`。

**多个 Agent 能一起用吗？**
账本就是一个普通文件，所以在会话或 Agent 之间交接没有问题：下一个运行 `render` 接着干就行。
目前还不支持多个写入者同时写，请由一个协调者负责更新。

## 参与贡献

欢迎报 bug、在更多 Agent 上实测、补翻译。见 [CONTRIBUTING.md](CONTRIBUTING.md)。跑测试：

```bash
python -m unittest discover -s tests
```

## 许可证

[MIT](LICENSE)
