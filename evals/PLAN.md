# Evaluation proposal

Status: plan only. No benchmark runner, optimization, or results have been added.
Implement after instructor review; keep main's small CLI unchanged.

## Question

Does requiring the agent to inspect the surrounding function and relevant
helpers before reaching a conclusion reduce missed issues, without increasing
false alarms or exceeding the same run budget?

## Dataset

Use OWASP BenchmarkPython, which includes vulnerable and non-vulnerable cases
with expected category/CWE labels:
https://github.com/OWASP-Benchmark/BenchmarkPython
https://owasp.github.io/www-project-benchmark/

Pin a specific commit before selecting cases. We already have a workshop cache
associated with f1291485808b66e20ddb6b01b10dc71b3df8c8ba; verify that provenance
and source hashes before using it. Do not run the deliberately vulnerable app.

Start with 12 small cases: four each for SQL injection, command injection and
path traversal, balanced between vulnerable and non-vulnerable labels. Allocate
six cases for development and six held out, each balanced by category and label.
Avoid placing near-identical flow variants in both splits. Inspect dependencies
and the expected-result labels manually before freezing the manifest.

Create a source-only fixture per case with required helpers. Keep expected-result
CSV, benchmark README, label-bearing comments/metadata and scorer files outside
the agent's selected snapshot. Preserve executable source and record any comment
removal plus original line mapping. Do not supply vulnerability categories or
expected outcomes in the review question. Selection must fit the tool's file and
byte limits; silently dropping a required helper invalidates that case.

This measures scoped source review, not full-repository discovery performance.
Public benchmark examples can be present in model training data; results are an
illustration, not evidence of broad real-world security accuracy.

## Comparable runs

A: current instructions, with the same report contract used in both arms.
B: identical tools/model/question/budgets, plus one evidence-checking instruction:

“Before judging a candidate, read the surrounding function and relevant helpers.
Do not decide from a search snippet alone. If you cannot obtain that context,
state the missing evidence and the limitation.”

This is a hypothesis, not a promised gain. The earlier workshop had an agent
miss a shell invocation after seeing only a search snippet; use that failure to
motivate the idea, never as the held-out success case. Freeze B after inspecting
only the development set. Keep the holdout closed until the final comparison.

First add submit_report to an evals branch derived from dev, validate its paths
and ranges, and use it identically for A and B. This provides machine-readable
findings and an explicit accepted/incomplete status; it does not judge correctness.

## Scoring

Record TP/FP/FN/TN by expected case/category; deduplicate repeated findings.
Require matching source evidence and manually audit claimed findings so merely
mentioning a category is not a hit. A clean outcome needs an accepted report.
Timeouts, provider errors, invalid reports and budget stops are incomplete,
never true negatives. Report completion rate separately and do not silently
drop failed attempts. Also report precision, recall, tool/model call counts,
latency and reported token usage (unknown when the provider omits it).

An empty accepted report is not necessarily a true negative: check the case's
expected label. Show any recall gain alongside false positives and added cost.

## Run budget and demonstration

After approval, smoke-test two development cases first. Use eight model calls
and 120 seconds per run in both arms. Proposed full demonstration: two attempts
per case per arm, 48 runs total; agree on an aggregate usage/cost cap before
running the batch. Save every attempt and provider failure, with no hidden
retries or selecting only successful results. If the cap permits fewer runs,
label the demonstration exploratory and show the actual sample size.

Present the baseline trace, the missing context, the one instruction change,
and the complete comparison table. Show a remaining failure or tradeoff. If B
does not improve the held-out results, report that result rather than inventing
an improvement or tuning against the holdout. Semgrep can be a later independent
experiment, not part of this first change.
