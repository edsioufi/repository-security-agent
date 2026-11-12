# Cross-file review experiments

These are reproducible development experiments, not a broad accuracy benchmark.
See `results/REPORT.md` for the retained outcomes and limitations.

The first case adapts the libpcap example in
[JITVul, ACL 2025](https://aclanthology.org/2025.acl-long.1490/), using the
[upstream fix](https://github.com/the-tcpdump-group/libpcap/commit/33834cb2a4d035b52aa2a26742f832a112e90a0a)
and its immediate parent. Labels and source hashes live outside model-visible
fixtures. No application or vulnerable service is run.

- `PROTOCOL.md`: original frozen function-level comparison.
- `PHASE2.md`: explicitly exploratory investigation/output changes.
- `SCENARIOS.md`: patch comparison and recorded amendments.
- `WHOLE-REPO.md`: whole CPython input versus tool navigation, no relevance search.
- `score.py`: citation visibility checks, separate from manual semantic audits.
- `verify_guard.py`, `verify_symlink.py`: isolated ground-truth checks.

## Reproduce

Use the repository's virtual environment and dependencies. Download the public
pinned libpcap archives to `/tmp/libpcap-before.tar.gz` and
`/tmp/libpcap-fixed.tar.gz`, then run `python -m evals.crossfile.prepare /tmp/libpcap-before.tar.gz /tmp/libpcap-fixed.tar.gz`.
The script verifies source against `manifest.json` and blanks comments while
preserving strings and line positions. Read its archive layout requirements.

For CPython, download
`https://github.com/python/cpython/archive/refs/tags/v3.13.0.tar.gz` to
`/tmp/cpython-v3.13.0.tar.gz`. The recorded archive SHA verifies the exact input.
Only regular UTF-8 text files enter the whole-repository input; every binary or
non-UTF-8 exclusion is recorded. No relevance-based selection is performed.

Set `GEMINI_API_KEY` privately in the environment. Never commit the key or use
the developer's private key path. From the repository root:

```sh
python -m evals.crossfile.verify_guard
python -m evals.crossfile.verify_symlink
python -m evals.crossfile.scenarios
python -m evals.crossfile.whole_repo
```

The live runners retain existing records and never replace failed attempts.
They share `runs/budget.json`; do not run them concurrently. The current session
ledger includes prior work; use a fresh ledger only for a separately authorized
experiment, preserving prior records. Current runs use Gemini 3.8 Flash after
provider rejection of Gemini 2.5 and availability failures on 3.5 Flash-Lite.
Read the protocols before spending money. Snapshot and results directories are
separate so models never receive ground truth or previous answers.

The capacity test uses the free count-tokens endpoint. It distinguishes an
actual token overflow from an HTTP/payload rejection and a provider outage.
It does not treat failure to submit the whole repo as a review-accuracy score.

For a UI demonstration, use a live run. The saved traces are audit evidence,
not a substitute for a live interaction.
