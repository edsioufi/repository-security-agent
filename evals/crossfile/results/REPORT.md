# Results: whole repositories and cross-file patch review

## Whole repository: capacity failure confirmed

CPython v3.13.0: 4,724 regular UTF-8 text files, including documentation and
tests, concatenated in path order with line numbers. No relevance search,
semantic selection, or truncation. Binary/non-UTF-8 exclusions are recorded.

Provider count: **48,957,530 input tokens**, versus Gemini 3.8 Flash's reported
**1,048,576-token limit** (46.7 times the limit). The full count returned;
we did not submit a knowingly over-limit paid generation request. A separate
8-million-character prefix measured 2,868,445 tokens; it was a capacity
measurement only, never a truncated review input.

The agent had access to the same complete text corpus through the unchanged
three navigation tools. Its first model call returned provider 504. Therefore:
whole-repo overflow is demonstrated; successful agent navigation is NOT.
This is capacity evidence, not an agent accuracy win.

The investigation question concerned SimpleHTTPRequestHandler and symlinks.
An isolated execution of the pinned translate_path implementation verified
that a symlink can resolve outside the configured directory, while ordinary
`..` components are removed. No HTTP server was started. This is documented
behavior, not a claim of a newly discovered vulnerability.

## Patch review: no demonstrated advantage

The case adapts JITVul's published libpcap CVE-2019-15164 example. The fixed
patch is the upstream fix; the vulnerable patch is its explicitly synthetic
reversal, not a real historical PR. Both arms got identical diffs. Agent tools
could inspect the resulting repository; the remote connection implementations
in pcap.c and pcap-rpcap.c were unchanged and absent from the diff.

The Gemini 3.5 Flash-Lite patch outputs selected the expected before/after
labels in their raw prose, but all four were malformed JSON. On manual review,
the agent searched for pcap_open yet did not inspect the cross-file remote
connection implementation. Neither arm established the complete mechanism.
These outputs are preserved, not silently repaired or counted as successful
structured responses. The conspicuous URL guard also makes this patch a weak
example for demonstrating that retrieval is necessary to guess the label.

Four separately labeled Gemini 2.5 attempts returned 404 (unavailable to this
account). Four Gemini 3.8 attempts returned provider 503/504. No pooling across
models, hidden retries, or replacement of failed attempts. Current-generation
model results therefore say nothing about comparative review accuracy.

## Earlier development retained

Original frozen function-level pilot: single completed 2/6 (one correct fixed
label, one appropriate abstention); agent completed 3/6 (two correct fixed
labels, one vulnerable-version miss). Neither arm achieved the full grounded
rubric. Seven attempts were incomplete. The next four investigation-prompt
attempts were incomplete. These are tiny known-case development experiments,
not held-out accuracy estimates.

The superseded static-retrieval batch had already started when the whole-repo
instruction arrived. Its one malformed single response and interrupted agent
record remain under raw/large, but are excluded from the requested comparison.
No relevance search enters the whole CPython baseline.

## What this supports

- Pasting the entire large repository is not viable for this model.
- The system needs a way to acquire relevant context incrementally.
- We have not shown that this agent does so reliably, or beats a single call
  on PR review. Tool availability and correct-looking labels are insufficient.
- A single call may work when its supplied context is enough. These results
  do not establish when that is true across real PRs.

The next useful run is the same declared comparison when provider calls are
reliable, not another favorable-case search. A stronger PR case should hide
the determining behavior in an unchanged implementation rather than exposing
an obvious removed guard. That case must be frozen before comparing outputs.

## Audit and reproduction

All records are in raw/; attempts.json indexes statuses. Source hashes and
binary exclusions are in raw/whole-repo-current/manifest.json. Read the parent
README and protocols before running. Manual semantic review was performed by
the implementing assistant, not an independent security reviewer.

Cost accounting retains conservative reservations for calls without reported
usage, so the total below is NOT an invoice. It includes all earlier evaluation
work in this session, not only these experiments.

Combined ledger including unknown-usage reserves: **$2.2184**, below the authorized $5.

Validation: 17 automated tests; isolated upstream URL-guard assertions and CPython symlink checks.
