# Jev Skill Suggester

[简体中文](README.md) · [Examples](docs/examples.md) · [Validation](docs/validation.en.md) · [Design](references/design.md)

Use TypeSafe Jev to recommend at most one installed skill for a task. Jev first ranks descriptions, then checks a small pool of entrypoint excerpts. It can return **no useful skill** or **uncertain**. A skill explicitly requested by the user takes precedence through deterministic local lookup.

This is a **Codex skill and standalone Python CLI** for large catalogs or overlapping skill descriptions. It suggests which entrypoint to read first. It does not execute or install the selected skill, modify agent settings, or register automatic hooks.

## Quick start

Requires **Python 3.10+**, using only the standard library. No `pip install` is needed. Offline mode needs no key; Jev mode requires a [TypeSafe](https://typesafe.ai/) API key and uses the pinned `jev-1.13.0` model.

```bash
git clone https://github.com/win4r/jev-skill-suggester.git
cd jev-skill-suggester

# Inspect your local catalog without API calls
python3 -I -B scripts/suggest.py catalog

# Default local mode: keyword candidates, not a semantic recommendation
python3 -I -B scripts/suggest.py suggest \
  --task 'Format an existing article for WeChat without publishing'

# Real Jev inference, hidden key entry, and a NEW report file
mkdir -p results
python3 -I -B scripts/suggest.py suggest \
  --task 'Format an existing article for WeChat without publishing' \
  --mode jev --prompt-key --out results/wechat.json
```

These commands use your own skill catalog. This repository does not bundle the skills selected in the recorded evaluation. Missing skills or different descriptions will change the outcome. Local mode always returns `local_only` and `suggestion: null`; the first keyword match is not a Jev decision.

### Install as a Codex skill

From the cloned directory, copy the six runtime files using this snippet. It refuses an existing target directory rather than overwriting an installation:

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

In a new session, ask:

> Use $jev-skill-suggester to recommend an installed skill for formatting an existing article for WeChat, preserving the wording and without publishing it.

Other agents can invoke the CLI with explicit `--root` directories. Codex and the standalone CLI have been tested; automatic discovery and invocation conventions in other hosts have not.

## How it works

1. Read skill names, descriptions and entrypoint bodies within the selected filesystem scope. Exclude this suggester and skills that prohibit implicit invocation.
2. Resolve user-named skills with `--require`, without calling Jev.
3. Use Jev `Choice` to rank each description batch and a separate `Noul` to assess whether that batch is useful. Retain at most three candidates per batch.
4. Review bounded body excerpts with another `Choice` and a separate fit `Noul` for each candidate.
5. The host reads the complete selected entrypoint, checks active-session availability, user constraints and tools, then decides how to proceed.

A suggestion requires fit ≥ 0.80 and Choice confidence ≥ 0.65. These are exploratory thresholds, **not calibrated correctness probabilities**. Jev returns typed decisions, not written explanations. The host should explain relevance from the actual skill description.

## Catalog scope and advanced usage

Without source arguments, discovery scans `~/.codex/skills` and `~/.agents/skills`. **Any `--root` or `--skill-file` replaces both defaults.** Repeat every source you intend to include:

```bash
python3 -I -B scripts/suggest.py catalog \
  --root ~/.codex/skills \
  --root ~/.agents/skills \
  --root /path/to/project/.agents/skills

# Use only when the user actually named this skill; no remote inference
python3 -I -B scripts/suggest.py suggest \
  --task 'Use wechat-editorial-studio to format this article' \
  --require wechat-editorial-studio

# File input, a restricted candidate set, response caching and request budget
python3 -I -B scripts/suggest.py suggest \
  --task-file /path/to/task.txt \
  --root /path/to/skills \
  --allow writer --allow editor \
  --mode jev --prompt-key --max-calls 6 \
  --cache-dir results/private-cache --out results/new-report.json
```

Replace `/path/to/...`, `writer` and `editor` with actual files and skill names. Even a fully cached Jev invocation currently requires a key to initialize the client.

| Option | Purpose |
|---|---|
| `--skill-file PATH` | Include an exact `SKILL.md` entrypoint; repeatable |
| `--allow NAME_OR_ID` / `--exclude NAME_OR_ID` | Restrict scope; repeatable; explicit selection cannot bypass them |
| `--require NAME_OR_ID` | Honor an explicit user selection; use catalog IDs for duplicate names |
| `--task-file PATH` | Read a longer task from a file instead of command arguments |
| `--cache-dir PATH` | Enable a 24-hour response cache keyed by task, model, questions and skill content |
| `--max-calls N` | Limit HTTP attempts to 1–64, default 12; retries count |
| `--trace` | Include actual payloads in reports, including task text and skill excerpts |
| `--out PATH` | Create a new JSON report; parent must exist; never overwrite |

Plugin caches are not automatically scanned because they may contain disabled or stale installations. Supply exact entrypoints from the active session through `--skill-file`. Filesystem installation does not prove active-session availability. Directory symlinks are skipped with warnings; explicitly target a known linked directory's entrypoint if needed. The final `SKILL.md` file itself must be a regular non-symlink file.

## Results and observed behavior

This is a **compact summary** from the first live evaluation. Local paths and full call records are omitted; it is not the complete CLI JSON or a raw HTTP envelope:

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

The task asks to format an existing article for WeChat while preserving its wording and without publishing. In actual CLI output, `suggestion` is an object with fields such as `name`, `id` and `path`, or `null`. Integrations must inspect `status`, not just the process exit code.

| Status | Meaning |
|---|---|
| `suggested` | Passed exploratory thresholds; host must read and review the full entrypoint |
| `explicit_selection` | Found the user-named skill without Jev inference |
| `none` | No useful match within the eligible scanned catalog |
| `uncertain` / `ambiguous` | Insufficient evidence or a non-unique name |
| `local_only` | Offline keyword candidates only |
| `unavailable` | Named skill is absent or filtered out |
| `incomplete` | API failure, budget, candidate limits or changed input prevented completion |

Exit `0` means the procedure completed, including `none`, `uncertain` and `local_only`; `2` means input/setup/output error; `3` means an incomplete Jev pipeline. A result is neither execution authorization nor a security assessment.

The 2026-09-19 evaluation used 24 local entrypoints, 23 eligible skills and 16 tasks labeled before inference:

| Metric | Observed result |
|---|---|
| Expected complete outcomes | 15/16 |
| Positive tasks | 12/12 selected the expected skill |
| Negative tasks | 3/4 returned `none`; an uncovered Trello task returned `uncertain` |
| Incorrect final suggestions | 0/16; this does not mean 100% accuracy |
| HTTP attempts / input / output | 45 / 230,067 tokens / 12,639 tokens |
| Median task latency | 5.05 seconds |
| Cached replay | 3 cache hits, 0 additional HTTP calls |

At the evaluation's assumed rate of $0.042 per million input tokens, estimated input cost was **$0.009662814**. This is not an invoice reconciliation; see [TypeSafe models](https://docs.typesafe.ai/models) for current pricing. Tasks were authored by the development host, with no independent label review or baseline comparison against direct host selection. These results do not establish production accuracy, overall savings or better task completion.

See [code and response examples](docs/examples.md), [validation details](docs/validation.en.md) and [all 16 sanitized records](examples/live-results.sanitized.json). No recommended skill was executed during the evaluation.

## Data handling and limits

- **Remote data:** Jev mode sends task text, skill names/descriptions, opaque IDs, content hashes and bounded excerpts to the official TypeSafe endpoint. Catalog path fields are omitted; referenced files and scripts are not read. Paths already embedded in task or skill prose are not automatically anonymized.
- **Credentials:** use hidden `--prompt-key` input or supply `TYPESAFE_API_KEY` through the caller's process environment. Do not put keys in command arguments, code or reports.
- **Reports:** ordinary reports contain local paths; `--trace` also contains full requests. Credential-pattern checks are incomplete. This repository publishes field-limited summaries only. New reports/cache files use mode 0600; new cache directories use 0700.
- **Large catalogs:** requests are batched under 28,000 UTF-8 bytes. Probabilities are not compared across batches. More than 12 pooled candidates produces `incomplete` and requires narrower scope. Excerpt truncation is reported.
- **Discovery warnings:** inspect `warnings` and `catalog_complete`. A no-match result over an incomplete inventory is not a global absence claim.
- **Failures:** a missing key is an error, not a successful offline fallback. Timeout is 45 seconds with one retry for 429/5xx, counted against the budget. Changed source files or invocation policies invalidate the recommendation.
- **Cache:** 24-hour TTL; even edits outside the visible excerpt invalidate relevant requests. Expired/invalid records are misses. Existing cache paths are never overwritten; remove expired records manually when needed.
- **Trust:** malicious descriptions may influence Jev. This tool is not a code audit, tool-availability check or permission system. The host retains the final decision.

## Tests and repository layout

```bash
# Offline unit tests; CI only performs offline checks
python3 -I -B tests/test_suggest.py

# Optional paid live evaluation: sends tasks and selected skill descriptions/excerpts
# The output directory must not already exist
python3 -I -B tests/run_live.py \
  --root /path/to/approved/skills --out results/my-live-run
```

The 25 unit tests cover metadata, files, explicit selection, invocation policies, two-stage decisions, failures, caching and output boundaries. A separate independent offline forward test checked eight workflows. The live runner uses expected labels in `examples/evaluation-cases.json`; adapt them **before** evaluating a different catalog. It saves full traces and local inventory data under your output directory. `results/` is Git-ignored.

```text
SKILL.md                         Agent entrypoint
agents/openai.yaml               Codex display metadata
scripts/suggest.py               Discovery, ranking, review and reports
scripts/jev_client.py            TypeSafe HTTP client and response validation
references/design.md            Thresholds, cache, budgets and limits
tests/                          Offline tests and optional live evaluation
examples/                       Labeled tasks and sanitized live results
docs/                           Examples and validation notes
```

Inspired by the [official TypeSafe two-stage skill suggestion cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion). Its Hermes benchmark is not a benchmark of this implementation. This is an independent project, not an official TypeSafe product.

Licensed under the [MIT License](LICENSE).
