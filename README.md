# Repository Security Agent

Three tools, one Google ADK agent, one terminal command. The model chooses tools,
ADK runs them, and their results return to the model before its next decision.
The CLI prints tool arguments, actual results, and the final answer. On web-ui,
an optional local web UI displays the same stream. No Docker, report framework,
or sample-app execution is required.

## Run it

Python 3.11+ on macOS/Linux (Windows: WSL):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

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

`tools/_source.py` is supplied file-access plumbing. The two files in `sample/` are synthetic source to inspect.

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

`main` keeps the small CLI implementation. `web-ui` contains optional interface
extensions. `evals` contains the evaluation experiments.

## Local web interface on web-ui

The server and HTML page live in `web_ui/`. Model callbacks and trace
formatting live in `web_ui/tracing/`, keeping the root focused on the agent
and CLI. The UI sends a fixed security-review request when you run it.

```sh
# Set GEMINI_API_KEY privately first.
.venv/bin/python -m web_ui
```

Open http://127.0.0.1:8767. Choose a local repository folder, then click
Run review to watch live tool activity and the answer. You can also paste a
folder path or supply one at startup: `python -m web_ui /path/to/repo`. The native picker
uses macOS Finder or Tk on other desktop systems; paste a path if unavailable.
The web UI always uses the live model and has no prompt presets or sample list.
The UI uses the same agent and runner as the CLI. It has no extra dependencies,
account system, upload endpoint, or deployment configuration. It binds only to
loopback and checks request origin, host, and a per-process request token.
Keep it local; it is not a production multi-user web service.

The proposed evaluation experiment is in [evals/PLAN.md](evals/PLAN.md). It is
a plan for review; no evaluation results or performance gains are claimed.

The live UI shows the ordered tool calls and expandable inputs and outputs for
each LLM call. Messages marked **sent again** are unchanged conversation
history carried into the next request, including previous tool results.
The trace shows visible messages and tool schemas, not API credentials or
private model reasoning. Refreshing the page clears the displayed run.
