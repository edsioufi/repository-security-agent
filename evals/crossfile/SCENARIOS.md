# Two workflow tests, declared before execution

Eight attempts: two workflows x two source versions x single/agent, once each.
Same source, model, concise format, generic investigation prompt and 12-call
agent limit as phase 2. No hidden retries, replacement runs, or selective results.
The shared ledger cap is now $5, as already authorized. Sequential execution.

## Large repository under a context budget
146 C/header files, approximately 2.2 MB, exceed our chosen input budget. This
is an operational context-budget test, NOT proof the entire repository exceeds
the model's advertised maximum context window. Both get a focal function and
file inventory. The single call additionally receives deterministic static
retrieval: files ranked by overlap with called symbols from the focal function,
alphabetical tie-break, whole files packed up to 190,000 raw bytes. No labels,
fix metadata or hand-picked filenames enter retrieval. Included paths retained.
Agent uses the three existing navigation tools. Both arms are limited to 256,000
cumulative serialized request bytes; agent pays for repeated history. Actual
input/output tokens and cost also reported. Bytes are a reproducible proxy,
not identical token allocation. The single-call bundle leaves serialization
headroom. A strong static retrieval baseline may tie or beat the agent.

## Patch review requiring unchanged context
Fixed case uses the real upstream fix's code diff (comments blanked as in the
existing corpus). Vulnerable case reverses that fix, a clearly labeled synthetic
regression, NOT a real historical PR. Both arms get exactly the same patch.
Agent tools see the resulting tree. No full focal function or file inventory is
provided in this workflow. Relevant pcap.c / pcap-rpcap.c implementations are
unchanged and absent from the patch. Scoring checks the concrete RPCAP outbound
connection mechanism, rather than merely noticing a removed URL guard.
This tests review of patch content, not GitHub PR metadata or discussion.

## Scoring and scope
Retain raw label, abstention, incomplete runs, actual tool traces, and verified
mechanism separately. Full grounded success uses PROTOCOL.md's cross-file
rubric. Audit actual supplied/retrieved lines per scenario. No broad accuracy
claim from one known CVE; all tests are exploratory development, not held-out.

## User amendment before any large-repository attempts
Remove static retrieval entirely. Whole-repository baseline must concatenate
ALL included repository files, in sorted path order, without relevance search.
The old batch crossed into the superseded relevance test before cancellation: one single-call output and one interrupted agent attempt are retained under runs/large, excluded from the requested whole-repo comparison. The 256 KB budget
no longer defines the whole-repository test: measure the provider's actual
advertised input-token limit, using its count-tokens API before generation.
A context overflow is a capacity result, not a security-detection score.

The four initial patch attempts all produced malformed JSON. Preserve those
raw results. Run four separately labeled `pr-stable` attempts with
`gemini-2.5-flash`, one per arm/version, all other patch settings unchanged.
This is a model/availability diagnostic, not a replacement of the prior batch.
Gemini 2.5 Flash official pricing is $0.30/M input and $2.50/M output including
thinking, matching the ledger rates. Do not pool model results.


## Availability correction
All four Gemini 2.5 attempts returned provider 404: model no longer available
to this account. They remain recorded. Provider recommends Gemini 3.8 Flash,
which the model-list endpoint confirms. Run four new `pr-current` attempts,
with provider JSON response mode and 4,000 output tokens to isolate formatting
failures. Same settings in both arms. Rates $0.75/M input, $3.75/M output,
verified against official Google pricing on 2026-11-12. Reserve $0.25 per
call, retain unknown usage, and enforce the shared $5 cap. This is the final
planned patch batch; report failures if it does not work.
