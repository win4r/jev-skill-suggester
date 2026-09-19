# 真实案例 / Live examples

[中文 README](../README.md) · [English README](../README.en.md) · [All 16 records](../examples/live-results.sanitized.json)

以下命令在仓库根目录执行，使用你自己的已安装技能范围。先创建 `results/`，输出文件须不存在。案例中的技能不随本仓库安装，目录不同，结果也可能不同。

Run these commands from the repository root against your own approved catalog. Create `results/` first; report files must be new. The selected skills are not bundled, so a different catalog may produce different results.

```bash
mkdir -p results
```

下面是 2026-09-19 首轮真实测试的响应摘要，不是完整 CLI JSON 或原始 HTTP 响应。`suggestion` 简化为名称，选择 ID 已转为候选名称，省略路径、描述、正文和请求；数值直接来自本地记录。实际 CLI 的 `suggestion` 为对象或 `null`。没有执行被推荐技能。

The following are compact summaries from the first live run, not complete CLI JSON or raw HTTP envelopes. Suggestions and opaque final Choice IDs are mapped to names; paths, descriptions, excerpts and requests are omitted. Values come directly from the recorded run. The actual CLI returns a suggestion object or `null`. No suggested skill was executed.

## 公众号只排版 / Format without publishing

```bash
python3 -I -B scripts/suggest.py suggest \
  --task '把已有文章排成微信公众号 HTML，保留原文字句，不要发布。' \
  --mode jev --prompt-key --out results/wechat_format.json
```

```json
{
  "status": "suggested",
  "suggestion": "wechat-editorial-studio",
  "http_attempts": 3,
  "host_review_required": true,
  "elapsed_ms": 5337.12,
  "choice_confidence": 0.92,
  "fit": 0.9
}
```

## 技术文章发布入口 / Select a publishing entrypoint

```bash
python3 -I -B scripts/suggest.py suggest \
  --task '把我已确认的这篇技术文章发布到掘金。' \
  --mode jev --prompt-key --out results/publish_article.json
```

```json
{
  "status": "suggested",
  "suggestion": "article-platform-publisher",
  "http_attempts": 3,
  "host_review_required": true,
  "elapsed_ms": 4800.37,
  "choice_confidence": 0.91,
  "fit": 0.86
}
```

这里只选择发布技能；该请求并未实际发布文章。 / This evaluation selected an entrypoint; it did not publish an article.

## 只读文档研究 / Read-only research

```bash
python3 -I -B scripts/suggest.py suggest \
  --task 'Consult the current TypeSafe documentation to explain when to use Jev Choice versus Noul in software. This is a read-only explanation request.' \
  --mode jev --prompt-key --out results/jev_reference.json
```

```json
{
  "status": "suggested",
  "suggestion": "typesafe-ai",
  "http_attempts": 3,
  "host_review_required": true,
  "elapsed_ms": 5156.91,
  "choice_confidence": 0.96,
  "fit": 0.85
}
```

只读任务也可受益于参考型技能，没有“必须执行外部操作”的过滤。 / Read-only tasks can benefit from reference skills; there is no action-only gate.

## 简单任务无需技能 / No skill needed

```bash
python3 -I -B scripts/suggest.py suggest \
  --task '17 乘以 23 等于多少？' \
  --mode jev --prompt-key --out results/no_skill_math.json
```

```json
{
  "status": "none",
  "suggestion": null,
  "http_attempts": 2,
  "host_review_required": true,
  "elapsed_ms": 3273.81
}
```

## 目录未覆盖且判断不充分 / Uncovered and uncertain

```bash
python3 -I -B scripts/suggest.py suggest \
  --task 'Add this card to my Trello backlog. I need a Trello-specific workflow.' \
  --mode jev --prompt-key --out results/no_skill_uncovered.json
```

```json
{
  "status": "uncertain",
  "suggestion": null,
  "http_attempts": 3,
  "host_review_required": true,
  "elapsed_ms": 5197.91,
  "choice_confidence": 0.29
}
```

此例期望 `none`，实际 `uncertain`，因此未计为正确完整结果。复核 Choice 的最高候选概率只有 0.48，最高适配值 0.41，均未构成可推荐的判断。

The expected outcome was `none`, so `uncertain` counts as a mismatch. The final Choice favored a workflow prompt skill, but its fit and confidence did not pass the recommendation gates:

```json
{
  "selection": {
    "type": "choice",
    "choice": "dynamic-workflow-prompt-builder",
    "confidence": 0.29,
    "probabilities": {
      "skill-creator": 0.21,
      "reddit-home-feed-research": 0.0,
      "none": 0.31,
      "dynamic-workflow-prompt-builder": 0.48
    }
  },
  "candidates": [
    {
      "name": "dynamic-workflow-prompt-builder",
      "fit": 0.41,
      "choice_probability": 0.48,
      "excerpt_truncated": false
    },
    {
      "name": "skill-creator",
      "fit": 0.31,
      "choice_probability": 0.21,
      "excerpt_truncated": true
    },
    {
      "name": "reddit-home-feed-research",
      "fit": 0.06,
      "choice_probability": 0.0,
      "excerpt_truncated": true
    }
  ]
}
```

## 重现范围 / Reproduction boundary

完整任务列表见 [evaluation-cases.json](../examples/evaluation-cases.json)。这是针对开发时目录的预设期望；在自己的目录上运行前应先核对并调整标签，不应看到答案后改标签。原始目录和请求未公开，因此此仓库支持程序复用和结果摘要核验，不提供完全相同输入的独立复现。

See [evaluation-cases.json](../examples/evaluation-cases.json) for all tasks. Labels describe the development catalog; review them before running against a different catalog, rather than changing them after seeing answers. The original private catalog and requests are not published, so this repository supports rerunning the software and inspecting result summaries, not independently reproducing the identical inputs.
