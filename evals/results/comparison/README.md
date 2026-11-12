# Recorded source review comparison

The harness works. The context instruction produced a small, inconsistent
improvement on held-out cases; this does not establish that agents are more
accurate than a single call. The saved traces do demonstrate an agent correcting
a report after receiving tool feedback.

Open `index.html` locally to inspect every report, source fixture and tool trace.
No API key or live model calls are needed for replay.

## Results

| Split / approach | Correct target decisions | False positives | Incomplete |
| --- | ---: | ---: | ---: |
| Development / baseline agent | 4/6 | 1 | 1 |
| Development / context agent | 4/6 | 2 | 0 |
| Development / single call | 3/6 | 1 | 2 |
| Held out / baseline agent | 10/12 | 2 | 0 |
| Held out / context agent | 11/12 | 1 | 0 |
| Held out / single call | 5/6 | 1 | 0 |

There are only six distinct held-out cases. Each agent ran twice on those same
cases; the single-call control ran once. Repeats are not independent new cases.
The single-call control received all fixture source up front. The agents could
retrieve source iteratively and had up to eight calls. All used
`gemini-3.5-flash-lite`, the same report schema and 2,000 output tokens per call.

No completed run missed its labeled vulnerability. This narrowly measures
target-CWE decisions, not the correctness of every explanation. One context
report included an extra, unverified CWE-79 finding. Some case-11 reports
overstated an arbitrary path existence check as file-content access. See the
assistant source-review notes in `audits.json`; this was not an independent
human audit.

Three incomplete attempts remain in the results: one baseline rate-limit error
and two single-call reports rejected for invalid evidence. No failed attempt was
silently retried or removed. Prompts were unchanged after opening the holdout.

## What to inspect

- `case-04 / baseline #1`: the reporting tool rejects missing required fields;
  the agent consumes that feedback and returns a valid, empty findings list.
  This illustrates recovery within the loop, not a guarantee of correctness.
- `case-10 / baseline #1` versus `context #1`: the context run correctly rejects
  a command-injection claim because a constant branch prevents input reaching
  the sink. Then inspect `context #2`: it regresses to a false positive despite
  describing the safe branch. The first-pass improvement did not fully repeat.
- `case-06`: both agent approaches produce a false positive. More investigation
  does not automatically yield better reasoning.

## Cost and provenance

48 attempts completed on 2026-11-11. Known reported token usage corresponds to
about **$0.1463** at standard paid text rates. The conservative local ledger
accounts for **$0.2963**, including an unknown-usage failure and two unused
reservations retained after correcting callback instrumentation. Both are below
the approved $5 cap. These are estimates, not an invoice; free-tier billing may
be zero. Per-arm tokens, calls and latency are in `summary.json`; latency includes
request pacing and is not a controlled performance comparison.

Sources derive from [OWASP BenchmarkPython](https://github.com/OWASP-Benchmark/BenchmarkPython)
at commit `f1291485808b66e20ddb6b01b10dc71b3df8c8ba`.
The manifest records original and transformed hashes. Selected test headers
credit Theo Cartsonis, 2025. Source is GPL-3.0; see `UPSTREAM-LICENSE.txt`.
Preparation neutralized labels in names/comments while preserving data flow,
sink expressions and line numbering. The vulnerable application was never run.
The public, synthetic source may be represented in model training data.

Published traces omit internal reasoning and opaque SDK fields. Original local
records remain outside Git. All 48 attempts, including failures, are included.
See ../../README.md for reproduction and the callback accounting correction.
