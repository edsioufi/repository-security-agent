# Whole-repository capacity and navigation test

User requested no relevance selection, truncation, or static retrieval. Use the
public CPython v3.13.0 archive, including all regular UTF-8 text files. Exclude
only binary/non-UTF-8 files; record every excluded path and archive/file hashes.
Do not execute repository code. Whole-source input is sorted, path-labelled,
line-numbered text. No semantic selection occurs.

Question: Can SimpleHTTPRequestHandler serve a file outside its configured
directory through a symbolic link? Trace URL-to-open behavior and distinguish
this from ordinary '..' path traversal. Ground truth is the pinned handler's
translate_path + send_head implementation, with documentation as corroboration.
This is a behavior investigation, not an undisclosed vulnerability claim.

Use Gemini 2.5 Flash. First submit the entire input to the provider's free
count_tokens endpoint and record model input_token_limit. If the provider
rejects request size, report a transport/payload failure, NOT a measured token
limit. If counted input exceeds the model limit, report context overflow and
skip knowingly invalid generation. No arbitrary local truncation. If it fits,
record that it fits; do not claim failure.

Separately run one agent investigation with the same question and access to ALL
those text files through the unchanged three repository tools. Twelve calls,
240 seconds, 256 KB cumulative serialized requests; same $5 combined cost cap.
The source loading adapter bypasses demo snapshot size/file-count limits, but
read/search result caps remain. Report these limits and any failures honestly.
No retries/replacement or accuracy claim from this single task.


Availability amendment: Gemini 2.5 generation is unavailable to this account.
Retain that capacity attempt; use Gemini 3.8 Flash for the labeled `current`
capacity and agent test, with its reported 1,048,576-token input limit. Apply
SCENARIOS.md's current-model JSON settings and cost accounting. No generation
is attempted for the over-capacity whole-source payload.

Capacity diagnostic amendment: the whole-payload count request did not return promptly. A free count of its first 8,000,000 characters returned 2,868,445 tokens, already exceeding the model limit. The full request completed before cancellation; its original response was restored from the log. This prefix is measurement only, never a truncated inference baseline.
