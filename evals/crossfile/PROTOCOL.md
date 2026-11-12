# Frozen paired case study

Question: does on-demand repository context help the model assess the actual
capture-source behavior of daemon_msg_open_req, with evidence?

Use the libpcap CVE-2019-15164 case studied in JITVul (ACL 2025), Appendix C.1.
This is an adaptation, not a replication of its models or introducing-commit
selection. Our pair is the documented upstream fix and its immediate parent.

Pin vulnerable 484d60cbf7ca4ec758c3cbb8a82d68b244a78d58 and fixed
33834cb2a4d035b52aa2a26742f832a112e90a0a. Keep all 146 .c/.h files from each
archive. Blank comments, preserving newlines and code, so the original TODO
warning does not reveal the missing guard. Do not execute the application.
Manifest, labels, version metadata and this protocol stay outside tool roots.
These public examples may be in training data; no contamination claim is made.

Both arms receive the same complete focal function with original line numbers.
Single: one call, no retrieval. Agent: identical starting evidence, same model,
three existing read-only exploration tools, up to eight calls. Both have 2,000
output tokens per call and 120 seconds. Same JSON final-response contract;
no report-validation tool in either arm, avoiding correction as a confound.
The agent has more available information and compute by design; this is a
workflow comparison, not a same-information reasoning test or proof that a
single call supplied all relevant context cannot solve the task.

Run three independent attempts on each version per arm, 12 total, alternating
order. No prompt tuning after results, hidden retries, replacing failures or
searching for another case because the single call succeeds. Keep all attempts.
Use a $1 combined conservative ledger cap including the prior $0.2963 estimate,
inside the approved $5 total. SDK retries stay disabled. Record full local
traces, model calls, usage, time and incomplete outputs. Publish sanitized traces.

## Predeclared scoring

Report three separate measures. An unsupported guess may get the label right;
it cannot pass the evidence rubric. Insufficient_evidence is an abstention, not
a correct negative. Incomplete and invalid JSON are reported separately.

1. Target classification: vulnerable for a, not_vulnerable for b. For positive
   answers the explanation must identify remote capture/request behavior, not
   an unrelated buffer bug. Negative means this issue is blocked, not globally
   safe. Record unrelated findings separately.
2. Evidence: exact quotes at valid line ranges, actually supplied/retrieved.
   Exclude invented or unseen citations. Exact validity alone is not semantic
   correctness. Manually audit the following rubric before calling it grounded.
3. Pair success: both versions correct in the same attempt; report across three
   attempts, not as six independent vulnerabilities.

Rubric for a grounded result (all required):
- Network-controlled source reaches the capture-opening call in daemon.c.
- pcap_open_live in pcap.c can dispatch remote sources to pcap_open_rpcap when
  HAVE_REMOTE is enabled. Do not assume the word "live" implies only local I/O.
- pcap-rpcap.c parses remote host/port and opens a client connection in
  rpcap_setup_session, reached through pcap_open_rpcap.
- For a, no URL-rejecting guard protects that call. For b, is_url rejects scheme
  plus :// before opening, and its implementation supports that conclusion.
- Correct impact/assumptions: server-side remote RPCAP connection, not arbitrary
  HTTP fetching or unauthenticated exploitability without evidence. Do not call
  a hypothetical remote build the unconditional behavior of every installation.

The assistant performs source audit; it is not independent expert validation.
This is one known-vulnerability case with a safe counterpart, not an accuracy
benchmark. Equal labels across arms are a valid outcome. Context-grounded
explanations and honest abstention are useful outcomes even without a label gain.

Sources:
https://aclanthology.org/2025.acl-long.1490/
https://github.com/the-tcpdump-group/libpcap/commit/33834cb2a4d035b52aa2a26742f832a112e90a0a
