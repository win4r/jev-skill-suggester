# Validation record

[简体中文](validation.md) · [README](../README.en.md)

Date: 2026-09-19. Version: 0.1.0. Requested and returned model: `jev-1.13.0`.

## Offline unit tests

`python3 -I -B tests/test_suggest.py`: 25 tests passed. Coverage includes:

- Plain, quoted and folded metadata; duplicate fields; distinct IDs for duplicate names.
- Symlinks, FIFOs, credential-like text, explicit-only policies and self-exclusion.
- Explicit selection without API calls and without bypassing exclusion filters; local mode without a semantic suggestion.
- Two-stage selection, no-skill decisions, insufficient absolute fit, low confidence and failure in the second stage.
- Source or invocation-policy changes during inference invalidating the result.
- Zero-call cache replay; task changes, edits beyond the excerpt, and invalid cache entries preventing reuse.
- New-only output files with mode 0600; unknown allow-list entries; exclusion of catalog path fields from requests.
- Complete candidate coverage across batches within the payload limit.

These tests validate behavior and boundaries, not semantic accuracy or complete security.

## Live Jev evaluation

Two explicitly selected roots contained 24 entrypoints. One prohibited implicit invocation, leaving 23 semantic candidates. Discovery produced no warnings. Plugin caches were not scanned; this was not an evaluation of every skill available in the active session.

The development host authored and labeled 16 tasks before inference. Labels were not independently audited. No thresholds or question wording were tuned to this run, and no reruns were selected for better answers.

| Task | Expected / observed |
|---|---|
| Format a WeChat article without publishing | `wechat-editorial-studio`, matched |
| Publish a confirmed technical article to Juejin | `article-platform-publisher`, matched |
| Check a local MCP server for exfiltration with Jev | `jev-security-scan`, matched |
| Edit writing with Jev and check meaning | `jev-humanize-writing`, matched |
| Create a reusable Codex skill | `skill-creator`, matched |
| Read the logged-in Reddit Home feed | `reddit-home-feed-research`, matched |
| Open interactive Claude Code in iTerm | `interactive-claude-iterm`, matched |
| Prepare a project for Claude Code | `claude-code-project-onboarding`, matched |
| Write a Codex /goal command | `goal-prompt-builder`, matched |
| Translate an English MOBI to Chinese | `translate-mobi-zh-minimax`, matched |
| Consult TypeSafe docs, read-only | `typesafe-ai`, matched |
| Consult Codex model/pricing docs, read-only | `openai-docs`, matched |
| Simple multiplication | `none`, matched |
| Translate one sentence | `none`, matched |
| Explain recursion in two sentences | `none`, matched |
| Trello-specific card workflow | Expected `none`; observed `uncertain` |

The Trello case retains an actual model confusion. The detail Choice distributed probability across `dynamic-workflow-prompt-builder`, `skill-creator` and `none`. The leading candidate probability was 0.48, Choice confidence 0.29, and maximum fit 0.41. It did not pass the recommendation gates. This was not a correct no-skill classification; zero incorrect final suggestions does not establish 100% accuracy.

- Expected complete outcomes: **15/16**.
- Positive tasks selecting the expected skill: **12/12**.
- Negative tasks returning `none`: **3/4**; one returned `uncertain`.
- Incorrect final suggestions: **0/16**.
- HTTP attempts: **45**, all successful; no failed attempts or retries.
- Input tokens: **230,067**; output tokens: **12,639**.
- Estimated input cost: **$0.009662814** at the evaluation's assumed $0.042/million input tokens, not an invoice reconciliation. See [pricing](https://docs.typesafe.ai/models).
- Median end-to-end task time: **5,052.875 ms**, including local reads, sequential inference and network latency.
- The eligible descriptions were split into two batches. Positive tasks used two ranking requests plus one detail request; the three clear no-skill tasks stopped after ranking.
- A replay of the first case produced **3 cache hits, 0 additional HTTP calls and 0 current-run billable input tokens**.

## Public evidence and reproducibility

[The sanitized JSON](../examples/live-results.sanitized.json) retains tasks, labels, outcomes, candidate scores, latency, token usage and per-call timing/usage. Final Choice IDs are mapped to candidate names. Local paths, the full catalog, descriptions, body excerpts, request payloads and input hashes are omitted. This is neither a raw HTTP capture nor complete CLI output.

Full requests and client-validated responses remain in the developer's local records. The public export retains runtime/fixture SHA-256 hashes from the pre-run manifest; these were checked against the published files. Readers can run the same program against their own catalog, but the private original inputs are not available for an identical independent reproduction. The records are not an independent audit.

## Independent offline forward test

A separate agent read the skill and exercised realistic offline CLI workflows. API calls, credentials, installations and code changes were prohibited.

Eight checks passed: keyword inspection and host entrypoint review for a WeChat task; ambiguity between actual duplicate-name installations; exact-ID selection; excluded and missing selections returning `unavailable`. All used zero API calls and did not evaluate Jev semantic quality.

One documentation ambiguity was found and fixed: wording that implied adding a `--root` or `--skill-file` appended to the default roots. These arguments actually replace the defaults. Documentation now states that explicitly and shows commands listing every intended source. The separate agent re-read the correction and confirmed the ambiguity was resolved. Detailed local records include machine paths and are not published; this section summarizes the process and result.

## Adoption boundary

Use this at task start, after a material goal change, or when overlapping skills make selection difficult. Do not invoke it on every message. There is no baseline comparison against direct host selection for task success, total tokens, total cost or latency. Overall savings and better completion rates have not been established.

Most tasks had clear intent and limited difficulty. All plugin catalogs, large catalogs, realistic multistep tasks, adversarial descriptions and mixed-language requests have not been systematically evaluated. Prompt injection may still affect decisions. Recommendation, availability checks, security review and execution authorization remain separate responsibilities.

The skill does not install global hooks, edit Codex settings or execute candidates. The host retains its skill catalog and makes the final decision after reading the complete entrypoint.
