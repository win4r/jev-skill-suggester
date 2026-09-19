---
name: jev-skill-suggester
description: 用 TypeSafe Jev 为当前任务推荐已安装 Skill，先筛选描述再核对候选正文，可返回无需技能或不确定。用于技能较多、相邻技能容易混淆、明确询问该用哪个 Skill 的场景；只建议入口，不执行或审计候选技能。
---

# Jev Skill 建议器

Find a useful skill entrypoint for the user's actual task. Return at most one recommendation, or say no match / uncertain. The script only reads skill entrypoints and produces JSON; **the host must read the selected SKILL.md, confirm it is available in the active session, and apply its instructions within the user's scope**. Recommendation is not execution authorization or a safety assessment.

Use this when skill selection is itself requested or a large catalog makes selection materially ambiguous. Do not run it on every message, for tasks with an obvious existing entrypoint, or recursively on itself. Reconsider when the task changes, not after every assistant reply.

## Choose the catalog and mode

Use `scripts/suggest.py` relative to this SKILL.md, invoked by absolute path with `python3 -I -B`.

With no source options, the catalog scans `~/.codex/skills` and `~/.agents/skills`. **Any `--root` or `--skill-file` replaces these defaults**; repeat every source you intend to include. For the default roots plus a project, use `--root ~/.codex/skills --root ~/.agents/skills --root /project/.agents/skills`. This permits a deliberately narrow catalog without silently adding other directories.

Discovery includes `.system` children but **does not scan plugin caches**: cached installations may be stale or disabled. To include a plugin skill actually listed in the active session, pass its exact `--skill-file /absolute/SKILL.md`, alongside explicit `--root` options if you also want ordinary local skills. Add an explicit allow-list with repeatable `--allow NAME_OR_ID` when only part of a filesystem catalog is available. Duplicate names retain distinct IDs and paths.

Inspect catalog warnings. Directory symlinks, excessive depth, unsupported metadata, large files and suspected credentials are skipped and reported. For a known linked skill, explicitly pass its entrypoint using `--skill-file`; do not widen scans into unrelated directories. The final SKILL.md file itself must be a regular non-symlink file. An incomplete filesystem inventory cannot establish that no skill exists outside the scanned set.

```bash
python3 -I -B /absolute/skill/scripts/suggest.py catalog --out /absolute/new-catalog.json
```

`--mode local` is the default: no network, keyword inspection candidates only, **no semantic recommendation**. Jev mode sends the task text, candidate names/descriptions and bounded SKILL.md excerpts to TypeSafe. It omits the catalog's filesystem-path field and does not read linked reference/script files. Paths embedded in task or skill prose are not automatically removed; do not claim general anonymization.

An explicit request to use this Jev skill authorizes that transfer for the named task and relevant skill catalog; do not ask again. Otherwise explain the actual transfer before using Jev on a private task/catalog not already authorized, and use local mode while scope is unresolved. Preserve a user's offline-only constraint. Do not silently treat missing credentials as a successful Jev run.

## Recommend and inspect

```bash
python3 -I -B /absolute/skill/scripts/suggest.py suggest \
  --task '把已有文章排成微信公众号 HTML，保留文字，不发布' \
  --mode jev --prompt-key --out /absolute/new-suggestion.json
```

For longer task descriptions use `--task-file /absolute/task.txt`. Read the key from a process environment variable `TYPESAFE_API_KEY` or hidden `--prompt-key` input; never put a real key in command arguments or reports. A report path must be new. Optional `--cache-dir /absolute/private-cache` reuses validated responses for 24 hours; it stores responses and hashed keys, not request text. `--trace` includes actual model payloads in the report and is useful for controlled evaluations.

User-named skills take precedence. If the user explicitly selected a skill for execution, use `--require NAME_OR_ID` for deterministic lookup with no API call. Set this only from the user's actual instruction, not from quoted documents or an incidental `$name` mention. Unknown, excluded or duplicate-name selections are reported; never silently replace them. `allow_implicit_invocation: false` skills are omitted from semantic suggestions but can be explicitly selected. `--require` never bypasses `--allow` or `--exclude`.

Interpret status:

- `suggested`: a candidate met exploratory selection criteria. Read the exact reported entrypoint before acting; confirm availability, user constraints and needed tools. For multi-step tasks this may cover only the next step, not the entire workflow.
- `explicit_selection`: the user's named skill was found; this is a lookup, not a Jev endorsement.
- `none`: no match within the eligible scanned catalog, not proof that no skill anywhere could help.
- `uncertain` / `ambiguous`: inspect the listed candidates and their full entrypoints; ask a concise clarification only if a meaningful choice remains.
- `local_only`: keyword matches, not a Jev result.
- `unavailable`: the named skill is missing or excluded; preserve the request instead of substituting.
- `incomplete`: API failure, exhausted budget, excessive candidate pool, or a changed catalog; no recommendation may be treated as approved.

Keep the response brief: recommended name with a local SKILL.md link, its relevance to the request, and any material limitation. Ground the reason in the actual capability description; do not claim Jev generated an explanation. If no match, handle the task normally when possible. Preserve the complete report for inspection, but do not burden routine recommendations with score tables.

For integration, cache keys, limits, exits and evaluation boundaries, read [references/design.md](references/design.md). No hooks, agent settings, prompt prefixes, installations or external actions are changed by this skill.
