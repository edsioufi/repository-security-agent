# Source review evaluation

Compare three approaches on a pinned, scoped OWASP BenchmarkPython subset:

- baseline: the repository agent plus a validated final reporting tool.
- context: exactly the same, with one instruction to inspect surrounding
  functions and relevant helpers before deciding.
- single: one call with all fixture source supplied up front and the same
  report tool, without iterative retrieval.

This is an exploratory test on 12 public synthetic cases, not a general
security-accuracy benchmark. Six cases are development and six held out.
Only the case's labeled CWE is scored; additional findings are listed separately.
Public-source memorization and common code idioms remain possible.

## Prepare

Download the archive for commit
f1291485808b66e20ddb6b01b10dc71b3df8c8ba from
https://github.com/OWASP-Benchmark/BenchmarkPython and extract it locally.

~~~sh
.venv/bin/python -m evals.prepare /path/to/extracted/source
~~~

The manifest records upstream and transformed SHA-256 hashes and original line
mapping. It remains outside each case's tool-visible source directory. Generated
fixtures are ignored by Git. Preparation only parses text; it never imports or
executes the vulnerable application. Category-bearing names and comments are
removed or neutralized; data-flow and sink expressions are preserved.
The original GPL-3.0 license is in UPSTREAM-LICENSE.txt. The upstream file
headers identify Theo Cartsonis, 2025, as author of the selected test cases.

## Run

Use the existing GEMINI_API_KEY environment variable. The example below shares
a persistent cost ledger across batches, with a 48-attempt ceiling. Never run
multiple runner processes concurrently against the same ledger.

~~~sh
.venv/bin/python -m evals.run --batch comparison --split dev --smoke
.venv/bin/python -m evals.run --batch comparison --split dev
# Freeze the instruction and manifest before opening the holdout:
.venv/bin/python -m evals.run --batch comparison --split holdout
.venv/bin/python -m evals.run --batch comparison --split dev --arms single
.venv/bin/python -m evals.run --batch comparison --split holdout --arms single
# Repeat all held-out agent pairs, without changing their prompts:
.venv/bin/python -m evals.run --batch comparison --split holdout --attempts 2
~~~

Existing attempt files are never replaced, including failed attempts. Request
retries are disabled; rate pacing is explicit. Each agent run has at most eight
model calls and 120 seconds. The one-call control has one model call. All arms
have the same model and 2,000-token output limit per call.

The ledger reserves $0.05 before a request and refunds the difference only when
usage is reported. An unknown-usage failure retains its reservation. A request
serialization cap bounds input size. Rates are standard paid text rates for
Gemini 3.5 Flash-Lite: $0.30/M input and $2.50/M output including thinking,
checked 2026-11-11 at https://aistudio.google.com/docs/pricing.
This is an estimate, not a billing statement; actual free-tier charges may be zero.

## Audit and score

Review every claimed positive against the fixture source. Write audits.json in
the batch directory keyed by attempt name, with valid_target_finding and a
rationale. Accepted reports with matching target-CWE findings remain
pending_audit until audited. Structural report acceptance does not verify a
vulnerability. Errors and missing attempts are incomplete, never true negatives.

~~~sh
.venv/bin/python -m evals.score evals/runs/comparison --attempts 1
~~~

For the completed comparison with repeated held-out agent runs, use
`--attempts 2`. Development and single-call runs remain one attempt each.
The [recorded results](results/comparison/README.md) include an offline HTML
viewer and all 48 sanitized attempts.

Reports, tool traces, usage and failures are kept under ignored evals/runs/.
After reviewing a completed comparison, publish a curated, sanitized result
bundle with all attempts included and clear limitations. Never promote a
scripted offline run as a live model result.

## Recorded execution

The completed comparison uses one development attempt per arm, two held-out
attempts for each agent arm, and one held-out attempt for the single-call
control: 48 attempts total. Repeats were declared before they ran, and neither
agent prompt was changed based on held-out results.

Two original single-call runs recorded two pre-model callbacks even though
ADK blocked the second provider request. Published model-call counts are
corrected to one, with the original callback counts and correction note
retained. Their incomplete statuses are unchanged. The ledger conservatively
retains the unused reservations; reported token costs are calculated separately.

The table scores target-CWE case decisions, not the quality of every sentence.
The source audit records impact overstatements and out-of-category findings.
