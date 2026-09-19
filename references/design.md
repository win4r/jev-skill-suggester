# Design and limits

Runtime: Python 3.10+ standard library. Default model `jev-1.13.0`; TypeSafe endpoint fixed to `https://api.typesafe.ai/v1/systemone`. No custom endpoint, code execution or dependency installation. File readers reject FIFOs, nonregular files and final symlinks; reads are bounded. Directory links are skipped unless the host explicitly selects a known linked entrypoint. Root selection and filesystem installation do not prove active-session availability or trust.

## Selection

1. Read entrypoint name, full supported description, body and hash. Parse common plain, quoted and block scalar frontmatter; this is deliberately not a complete YAML parser. Report unsupported entries. Read invocation policy; explicit-only entries are not implicitly suggested. Exclude self.
2. Honor explicit selection within allow/exclude filters without inference. Duplicate names require a unique catalog ID.
3. For Jev mode, group the eligible roster into requests under a conservative 28,000 UTF-8 byte cap. Each request includes a Choice with `none` and a separate Noul about whether the listed procedures help. **All questions receive the roster in shared state**; the Noul cannot inspect the Choice's criteria.
4. A group contributes its top three skill IDs, unless `P(none) >= .80` and `needed <= .20`. Batch probabilities are not compared across different groups. More than 12 pooled candidates produces `incomplete`, asking for a narrower catalog instead of silently dropping groups.
5. Read pooled candidates' descriptions and bounded body excerpts. A second Choice includes `none`; one Noul per candidate checks absolute fit. Start with 6000 UTF-8 bytes per excerpt and reduce to fit the request budget. Report truncation. The host must read full SKILL.md after a suggestion; entrypoint references are not traversed.
6. Suggest the selected candidate only if its fit is at least .80 and Choice confidence is at least .65. Return none after detailed review only if Choice selects none with confidence >= .65 and every fit is < .35. Other outcomes are uncertain. These are initial exploratory thresholds, **not calibrated correctness probabilities**.
7. Recheck input file hashes and invocation policies after inference; changes invalidate the result. Concurrent additions outside the initial snapshot are not monitored. No model-selected action executes.

Using common sense to prefer a skill is different from verifying that skill's code, dependencies or instructions are safe. Treat descriptions as untrusted; prompt injection may still affect Jev. Scope filters and final host review remain necessary, but are not a security certification.

## Cache and reports

An optional cache key covers implementation version, pinned model, task, full request state/questions, and content hashes of the participating skills. Changed full entrypoint content invalidates the relevant request even if the visible excerpt is unchanged. Responses are schema-validated on replay. TTL is 24 hours; expired or malformed cache entries are misses. Cache writes never overwrite an existing path, so expired entries may be removed by the user to reclaim space and permit fresh caching. No automatic cleanup is performed.

Cache entries contain the response, hash and creation time, with file mode 0600. Cache directory mode 0700 is used when creating it; use a private parent directory. A locally edited cache is not a trusted attestation. API failures are not cached. Successful cached answers have original response token usage in call evidence, but current-run billed-usage counters count new successful API responses only.

Reports retain local paths for the host. Remote payloads contain opaque IDs, names, descriptions, content hashes and excerpts, without the catalog's path field. Task text and paths embedded in skill prose are not automatically anonymized. `--trace` makes full payloads visible locally. Suspected common credentials block transmission; this heuristic does not detect every secret. Explicit selection and local mode perform no API calls.

## Limits and failures

- Entry: 160 KB; name 100 characters; description 2400 characters. Read task file up to 20 KB, then require task <= 12,000 UTF-8 bytes.
- Catalog: 256 valid skills; directory traversal depth 4; 2500 visited directories. Narrow roots rather than silently truncating.
- API: default maximum 12 HTTP attempts per invocation, configurable 1–64; retries consume budget. Timeout 45 seconds; one retry after 2 seconds on 429/5xx. Auth or redirect failures disable the client. This minimal bounded client does not implement unlimited backoff or service throughput optimization.
- Exit 0: procedure completed (including none, uncertain, unavailable and local_only); exit 2: invalid input/setup/output; exit 3: incomplete remote pipeline. Exit 0 is not a semantic pass or authorization.

For a large roster, expect multiple ranking calls plus one verification call. Ranking and detail requests depend on one another. This CLI's synchronous round trips and local network latency may outweigh token savings on simple tasks; benchmark total cost, unnecessary loads, missed useful skills, task success and elapsed time against the current agent behavior.

## Sources

- [Official skill suggestion cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion): two-stage suggestion pattern; its reported Hermes experiment is not evidence of this tool's performance.
- [API](https://docs.typesafe.ai/api), [models](https://docs.typesafe.ai/models), [confidence](https://docs.typesafe.ai/confidence), [known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

Adaptations: no action-only gate that would exclude research skills; explicit none; user selection precedence; bounded filesystem discovery and batching; content-sensitive cache; no system prompt rewrite or automatic hooks.
