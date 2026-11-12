"""Build a local results viewer and a sanitized, complete attempt bundle."""
import argparse
import json
from pathlib import Path
import shutil

from evals.score import summarize

ROOT = Path(__file__).parent


def publish(batch, output):
    summary = summarize(batch, 2)
    output.mkdir(parents=True, exist_ok=True)
    runs = []
    for path in sorted(batch.glob("case-*.json")):
        record = json.loads(path.read_text())
        if record.get("model_calls", 0) > record.get("max_model_calls", 8):
            record["pre_model_callbacks"] = record["model_calls"]
            record["model_calls"] = record["max_model_calls"]
            record["instrumentation_note"] = (
                "ADK invoked the pre-model callback before rejecting a second "
                "call. Only one provider request was sent. Original raw trace "
                "and callback count are retained; status remains incomplete."
            )
        events = []
        for event in record.get("trace", []):
            content = event.get("content") or {}
            for part in content.get("parts", []):
                if part.get("function_call"):
                    events.append({"type": "Tool call",
                                   "data": part["function_call"]})
                elif part.get("function_response"):
                    events.append({"type": "Tool result",
                                   "data": part["function_response"]})
                elif part.get("text") and not part.get("thought"):
                    events.append({"type": "Model response",
                                   "data": part["text"]})
            if event.get("error_code"):
                events.append({"type": "Error", "data": event["error_code"]})
        record["trace"] = events
        record["source_files"] = {
            p.relative_to(ROOT / "fixtures" / record["case"]).as_posix(): p.read_text()
            for p in (ROOT / "fixtures" / record["case"]).rglob("*.py")
        }
        runs.append(record)
        (output / path.name).write_text(json.dumps(record, indent=2) + "\n")
    for filename in ("summary.json", "audits.json"):
        shutil.copyfile(batch / filename, output / filename)
    shutil.copyfile(ROOT / "manifest.json", output / "manifest.json")
    shutil.copyfile(ROOT / "UPSTREAM-LICENSE.txt", output / "UPSTREAM-LICENSE.txt")
    data = json.dumps({"summary": summary, "runs": runs}).replace("<", "\\u003c")
    template = """<!doctype html>
<html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Source review comparison</title>
<style>
body {font:16px/1.5 system-ui;max-width:1100px;margin:40px auto;padding:0 24px;
background:#fafbfc;color:#182333}
h1 {font-size:30px} h2 {margin-top:32px}
table {border-collapse:collapse;width:100%;margin:24px 0}
th,td {text-align:left;padding:9px;border-bottom:1px solid #ccd3dc}
select {font:inherit;padding:8px;max-width:100%}
pre {white-space:pre-wrap;overflow-wrap:anywhere;background:#edf0f5;
padding:16px;font:13px/1.5 monospace}
details {margin:12px 0} summary {cursor:pointer;font-weight:600}
.notice {padding:16px;background:#fff1d6}
</style>
<h1>Does more investigation improve source review?</h1>
<p>Same model. Twelve source fixtures. All __RUN_COUNT__ recorded attempts are included.
Six development cases and six held out. Agent arms repeat held-out cases twice;
the single-call control runs once. These are saved live-model results.</p>
<p class="notice">This is a small exploratory comparison on public synthetic
code. It does not establish real-world security accuracy. An incomplete
review is never counted as a clean scan. Only each case’s labeled CWE is scored.</p>
<p><strong>Baseline:</strong> agent with read/search tools.
<strong>Context:</strong> same agent plus one instruction to inspect surrounding
functions and helpers.
<strong>Single:</strong> one call with all fixture source supplied up front.</p>
<h2>Results</h2><div id="totals"></div>
<h2>Inspect an actual run</h2><select id="select"></select>
<div id="result"></div><div id="trace"></div>
<script type="application/json" id="data">__DATA__</script>
<script>
const data=JSON.parse(document.querySelector('#data').textContent);
const totals=document.querySelector('#totals');
const table=document.createElement('table');
const header=table.insertRow();
['Split / approach','TP','FP','FN','TN','Incomplete','Pending audit'].forEach(x=>{
const th=document.createElement('th');th.textContent=x;header.append(th)});
for(const [name,t] of Object.entries(data.summary.totals)){
const row=table.insertRow();
[name,...['TP','FP','FN','TN','incomplete','pending_audit'].map(k=>t[k]||0)]
.forEach(x=>{row.insertCell().textContent=x})}
totals.append(table);
const select=document.querySelector('#select');
for(const [i,r] of data.runs.entries()){
const option=document.createElement('option');option.value=i;
const score=data.summary.rows.find(x=>x.case===r.case&&x.arm===r.arm&&x.attempt===r.attempt);
option.textContent=r.case+' / '+r.arm+' #'+r.attempt+' / '+(score?.outcome||r.status);
select.append(option)}
function show(){
const r=data.runs[Number(select.value)];
const result=document.querySelector('#result');result.replaceChildren();
const p=document.createElement('p');
p.textContent=r.status+' · '+r.model_calls+' model calls · '+
r.latency_seconds+' seconds · '+r.model;result.append(p);
const report=document.createElement('pre');
report.textContent=JSON.stringify(r.report||{error:r.error},null,2);
result.append(report);
const source=document.createElement('details');
const label=document.createElement('summary');label.textContent='Exact source fixture';
source.append(label);
for(const [name,text] of Object.entries(r.source_files)){
const pre=document.createElement('pre');pre.textContent=name+'\\n'+text;source.append(pre)}
result.append(source);
const trace=document.querySelector('#trace');trace.replaceChildren();
for(const [i,e] of r.trace.entries()){
const detail=document.createElement('details');
const title=document.createElement('summary');
title.textContent=(i+1)+'. '+e.type+' '+(e.data?.name||'');
const body=document.createElement('pre');
body.textContent=typeof e.data==='string'?e.data:JSON.stringify(e.data,null,2);
detail.append(title,body);trace.append(detail)}
}
select.addEventListener('change',show);show();
</script></html>"""
    (output / "index.html").write_text(template.replace("__DATA__", data).replace("__RUN_COUNT__", str(len(runs))))
    print(output / "index.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    publish(args.batch, args.output)
