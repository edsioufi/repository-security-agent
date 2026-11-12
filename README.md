# Repository Security Agent

Three tools, one Google ADK agent, one terminal command. The model chooses tools,
ADK runs them, and their results return to the model before its next decision.
The CLI prints tool arguments, actual results, and the final answer. On dev,
an optional local web UI displays the same stream. No Docker, report framework,
or sample-app execution is required.

## Run it

Python 3.11+ on macOS/Linux (Windows: WSL):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python cli.py --offline
```

Offline mode uses a **scripted fake model** with the real ADK runner and real
local tools. It needs no key or network and makes no security assessment.

For the live agent, set `GEMINI_API_KEY` privately in your terminal environment,
then run:

```sh
.venv/bin/python cli.py
.venv/bin/python cli.py sample --question "Follow user input to database access."
```

Use `--model MODEL_NAME` or `GEMINI_MODEL` to select another available Gemini
model. The default model is `gemini-3.5-flash-lite`.
Provider access and quotas still apply.

## Read these files in order

1. `tools/repository.py`: ordinary `list_files`, `read_file`, `search_code`
   methods with descriptions, arguments, bounded outputs, and error results.
2. `agent.py`: register those three methods in the Agent's `tools` list.
3. `cli.py`: send the question to ADK and display events. ADK owns the repeated
   model/tool exchange; the `async for` loop here displays that exchange.

`tools/_source.py` is supplied file-access plumbing. `offline.py` is only the
no-key fallback. The two files in `sample/` are synthetic source to inspect.

Try a tool directly, without ADK or an API key:

```sh
python3 -c 'from tools import RepositoryTools; t = RepositoryTools("sample"); print(t.read_file("app.py"))'
```

Then run the agent and point to: its requested arguments, the returned source,
and the final answer's use of that evidence. Change a tool description or the
question and observe whether the live model chooses a different investigation.
Adapt tool descriptions and review questions to the repository being inspected.

## Small, explicit boundaries

Only selected text files are available: no hidden paths, symlinks, common
secret-named files, binaries, or generated folders. Selection is limited to
500 files, 64 KB per file, and 1 MB total. Reads return at most 80 numbered lines
and 6000 characters; search returns at most 30 matches. Inspect truncation flags.
These filters cannot detect every embedded secret. Use the supplied synthetic
sample for initial runs; live runs send retrieved source to Gemini.

The run stops after at most 8 model calls or 120 seconds. Provider requests have
a 30-second timeout. A failed run is marked incomplete, not a completed review.
A completed response is not proof of a correct or comprehensive assessment.
There is no shell-execution tool and no automatic writing or publishing.

## Checks

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## Branches

`main` keeps the small CLI implementation. `dev` contains optional interface
extensions. Evaluation work will be planned and reviewed before implementation.

## Local web interface on dev

```sh
.venv/bin/python web.py sample --offline
# Live: set GEMINI_API_KEY privately, then omit --offline.
```

Open http://127.0.0.1:8767. Click Run review to inspect the repository and watch the streamed
tool activity and answer. The source folder is selected at startup, not through the browser.
The UI uses the same agent and runner as the CLI. It has no extra dependencies,
account system, upload endpoint, or deployment configuration. It binds only to
loopback and checks request origin, host, and a per-process request token.
Keep it local; it is not a production multi-user web service.

The proposed evaluation experiment is in [evals/PLAN.md](evals/PLAN.md). It is
a plan for review; no evaluation results or performance gains are claimed.
