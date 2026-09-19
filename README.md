# Jev Skill 建议器

[English](README.en.md) · [真实案例](docs/examples.md) · [验证记录](docs/validation.md) · [设计说明](references/design.md)

用 TypeSafe Jev 为当前任务推荐一个合适的已安装 Skill。先阅读技能描述筛选，再核对候选正文片段；允许返回“无需技能”或“不确定”。用户明确指定的技能通过本地查找优先处理。

适合已安装很多技能、相邻技能用途容易混淆、需要明确决定先读哪个 `SKILL.md` 的场景。它是一个 **Codex Skill + 独立 Python CLI**，不执行或安装候选技能，不修改 Agent 设置，不添加自动运行 hook。

## 快速开始

要求 **Python 3.10+**。运行时仅用标准库，无需 `pip install`。离线模式不需要 Key；Jev 模式需要 [TypeSafe](https://typesafe.ai/) API Key，固定使用 `jev-1.13.0`。

```bash
git clone https://github.com/win4r/jev-skill-suggester.git
cd jev-skill-suggester

# 读取本地技能目录，不访问 API
python3 -I -B scripts/suggest.py catalog

# 默认 local 模式：只给关键词候选，不给语义推荐
python3 -I -B scripts/suggest.py suggest --task '为已有文章做公众号排版'

# Jev 模式：隐藏输入 Key，并写入一个新的报告文件
mkdir -p results
python3 -I -B scripts/suggest.py suggest \
  --task '把已有文章排成微信公众号 HTML，保留原文，不发布' \
  --mode jev --prompt-key --out results/wechat.json
```

这些命令使用你自己的技能目录。本仓库不附带案例中被推荐的技能，未安装时不能得到同样结果。`local` 模式始终是 `local_only`，且 `suggestion` 为 `null`；不能把关键词第一名当作 Jev 的判断。

### 安装为 Codex Skill

在克隆目录中运行以下命令，只复制六个运行时文件。目标目录已存在时会报错，避免覆盖已有安装：

```bash
python3 - <<'PY'
from pathlib import Path
import shutil
target = Path.home() / '.codex/skills/jev-skill-suggester'
target.mkdir(parents=True, exist_ok=False)
for name in ['SKILL.md', 'LICENSE']:
    shutil.copy2(name, target / name)
for name in ['agents', 'scripts', 'references']:
    shutil.copytree(name, target / name)
print(target)
PY
```

打开新会话后调用：

> 使用 $jev-skill-suggester，为“把已有文章排成微信公众号 HTML，保留原文，不发布”推荐合适的已安装技能。

其他 Agent 可以通过 CLI 调用；使用 `--root` 显式指定该 Agent 的技能目录。此版本验证了 Codex Skill 与 CLI，未验证其他宿主的自动发现和调用约定。

## 工作方式

1. 在指定范围读取 `SKILL.md` 的名称、描述和正文，排除自身及不允许隐式调用的技能。
2. 用户明确点名时用 `--require` 本地查找，零 API 调用。
3. Jev 用 `Choice` 排序描述，并用单独的 `Noul` 判断该组技能是否有用；每组最多保留三个候选。
4. 复核候选的正文片段，再用 `Choice` 与每个候选的适配 `Noul` 决定是否推荐。
5. 宿主阅读被推荐技能的完整入口，核实当前会话可用性、用户限制和所需工具，再决定如何使用。

复核推荐门槛为适配值 ≥ 0.80、Choice confidence ≥ 0.65。这些是探索性门槛，**不是经过校准的正确率**。Jev 提供类型化判断，不撰写推荐理由；理由应由宿主依据实际技能描述说明。

## 目录范围与进阶用法

无源参数时扫描 `~/.codex/skills` 和 `~/.agents/skills`。**任意 `--root` 或 `--skill-file` 都会替代这两个默认源**；请重复列出全部想纳入的来源：

```bash
python3 -I -B scripts/suggest.py catalog \
  --root ~/.codex/skills \
  --root ~/.agents/skills \
  --root /path/to/project/.agents/skills

# 仅在用户确实点名时使用；没有远程推理
python3 -I -B scripts/suggest.py suggest \
  --task '请使用 wechat-editorial-studio 做排版' \
  --require wechat-editorial-studio

# 长任务、限制候选范围、缓存及 HTTP 尝试预算
python3 -I -B scripts/suggest.py suggest \
  --task-file /path/to/task.txt \
  --root /path/to/skills \
  --allow writer --allow editor \
  --mode jev --prompt-key --max-calls 6 \
  --cache-dir results/private-cache --out results/new-report.json
```

上述 `/path/to/...`、`writer`、`editor` 是占位符，需替换成实际文件或技能名称。缓存也可能完全命中；当前 CLI 仍要求在 Jev 模式下提供 Key。

| 选项 | 用途 |
|---|---|
| `--skill-file PATH` | 显式纳入一个准确的 `SKILL.md` 路径，可重复 |
| `--allow NAME_OR_ID` / `--exclude NAME_OR_ID` | 限制候选范围，可重复；`--require` 也不能绕过 |
| `--require NAME_OR_ID` | 处理用户明确选择；同名技能用目录中的 ID 区分 |
| `--task-file PATH` | 从文件读取任务，避免较长文本进入命令参数 |
| `--cache-dir PATH` | 开启 24 小时响应缓存，键含任务、模型、问题及技能内容哈希 |
| `--max-calls N` | 每次最多 1–64 次 HTTP 尝试，默认 12；包含重试 |
| `--trace` | 把实际请求写进本地报告，含任务和技能片段，公开前需审查 |
| `--out PATH` | 新建 JSON 报告，父目录须存在；不会覆盖已有路径 |

插件缓存可能含已停用或旧版本技能，因此不会自动扫描。可从当前会话的技能表取得准确入口，以 `--skill-file` 纳入；“文件存在”不等于“当前会话可调用”。目录符号链接默认跳过并报告，已知链接目录可显式指定入口；最终 `SKILL.md` 文件自身必须是非链接普通文件。

## 结果与真实效果

以下是首轮真实测试的**响应摘要**，省略本机路径和完整调用记录；不是完整 CLI JSON 或原始 HTTP 响应：

```json
{
  "task": "把已有文章排成微信公众号 HTML，保留原文字句，不要发布。",
  "status": "suggested",
  "suggestion": "wechat-editorial-studio",
  "choice_confidence": 0.92,
  "fit": 0.9,
  "http_attempts": 3,
  "elapsed_ms": 5337.12,
  "host_review_required": true
}
```

实际 CLI 的 `suggestion` 是包含 `name`、`id`、`path` 等字段的对象，或 `null`。集成时读取 JSON 的 `status`，不要只看退出码。

| 状态 | 含义 |
|---|---|
| `suggested` | 满足推荐门槛，宿主仍须阅读完整入口并核对任务 |
| `explicit_selection` | 找到用户点名的技能，未调用 Jev |
| `none` | 本次合格候选范围内无匹配，不代表所有技能都无用 |
| `uncertain` / `ambiguous` | 判断不充分或名称不唯一 |
| `local_only` | 只有离线关键词候选，没有语义推荐 |
| `unavailable` | 点名技能不存在或被过滤 |
| `incomplete` | API、预算、候选规模或输入变化导致流程不完整 |

退出码 `0` 表示流程完成，含 `none`、`uncertain`、`local_only`；`2` 表示输入/设置/输出错误；`3` 表示 Jev 流程不完整。任何结果都不构成执行授权或安全审核。

2026-09-19 在本地 24 个入口、23 个合格候选上测试 16 个预先标注任务：

| 指标 | 结果 |
|---|---|
| 符合预期完整结果 | 15/16 |
| 有匹配技能的任务 | 12/12 推荐预设技能 |
| 无匹配任务 | 3/4 返回 `none`；Trello 案例返回 `uncertain` |
| 错误给出最终推荐 | 0/16；这不等于 100% 准确率 |
| HTTP 尝试 / 输入 / 输出 | 45 / 230,067 tokens / 12,639 tokens |
| 每任务中位耗时 | 5.05 秒 |
| 缓存重放 | 3 次命中，0 次新增 HTTP 调用 |

按评估时采用的 $0.042/百万输入 tokens 估算，本轮为 **$0.009662814**；不是账单核对结果，当前价格请查 [TypeSafe models](https://docs.typesafe.ai/models)。测试是同一开发宿主编写的有限案例，没有与“宿主直接选技能”比较任务完成率、整体成本或耗时，不能据此宣称生产准确率或整体节省。

更多任务、代码和结果见 [真实案例](docs/examples.md)、[验证记录](docs/validation.md) 和 [16 个案例的脱敏 JSON](examples/live-results.sanitized.json)。案例中没有实际执行被推荐技能。

## 数据、限制与常见问题

- **发送什么？** Jev 模式发送任务、技能名称/描述、不透明 ID、内容哈希及有限正文片段到 TypeSafe 官方端点。程序不添加目录 `path` 字段，不读取引用文件或脚本；任务或正文中自行包含的路径不会自动匿名化。
- **Key 怎么传？** 使用隐藏输入 `--prompt-key`，或由调用方设置进程环境变量 `TYPESAFE_API_KEY`。不要把 Key 写进命令参数、代码或报告。
- **报告是否可以直接公开？** 默认报告有本机路径，`--trace` 另含完整请求。常见凭证模式检查不能识别所有敏感信息；本仓库只发布人工限定字段的摘要。新报告和缓存文件权限为 0600，新缓存目录为 0700。
- **目录很大怎么办？** 请求按 28,000 UTF-8 字节上限分组，跨组不直接比较概率；超过 12 个最终候选会返回 `incomplete`，需要缩小范围。正文片段截断会被标记。
- **读取警告怎么办？** 查看 `warnings` 和 `catalog_complete`，修正源范围；不要把不完整目录中的 `none` 解读成全局没有适合技能。
- **失败怎么办？** 缺少 Key 是错误；远程失败不伪装成功。单次超时 45 秒，429/5xx 最多重试一次，重试计入预算。文件或调用策略在推理期间变化会使推荐失效。
- **缓存怎么更新？** 有效期 24 小时；正文片段之外的修改也会失效。过期/非法记录不会复用；同一路径不自动覆盖，可手动清理过期缓存。
- **可以用来审计恶意技能吗？** 不可以。提示注入仍可能影响判断；本项目决定先读哪个入口，不能替代代码审计、可用性核实或权限控制。

## 测试与文件结构

```bash
# 离线单元测试；CI 也只运行离线检查
python3 -I -B tests/test_suggest.py

# 可选真实测试：隐藏输入 Key；发送任务和所选技能的描述/片段
# 输出目录必须不存在；这不是免费的离线测试
python3 -I -B tests/run_live.py \
  --root /path/to/approved/skills --out results/my-live-run
```

25 项单元测试涵盖元数据、路径、显式选择、调用策略、两阶段流程、失败、缓存和输出边界。另有 8 项独立离线前向流程检查。实时 runner 使用预先写在 `examples/evaluation-cases.json` 的期望标签；你自己的技能目录不同，需要先调整标签，不能直接套用 15/16 的结果。它会保存完整 `--trace` 与本机目录信息，`results/` 已被 Git 忽略。

```text
SKILL.md                         Agent 入口
agents/openai.yaml               Codex 展示信息
scripts/suggest.py               本地发现、筛选、复核和报告
scripts/jev_client.py            TypeSafe HTTP 客户端与响应校验
references/design.md            阈值、缓存、预算和限制
tests/                          离线测试与可选真实评估
examples/                       预设任务和脱敏真实结果
docs/                           案例及验证说明
```

思路参考 [TypeSafe 官方两阶段 Skill suggestion cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion)。其 Hermes 实验的改善幅度不代表本实现效果。本项目不是 TypeSafe 官方产品。

代码采用 [MIT License](LICENSE)。
