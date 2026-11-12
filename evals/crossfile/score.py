"""Check citations mechanically; semantic scores require a separate audit."""
import json
import re
import sys
from pathlib import Path

from evals.crossfile.run import ROOT, load_source


def visible_lines(record, info):
    shown = {}
    scenario = record.get('scenario')
    if not scenario:
        shown = {info['focal_path']: set(range(info['start_line'],info['end_line']+1))}
    else:
        name, number = None, None
        for line in record.get('question', '').splitlines():
            if line.startswith('FILE '):
                name = line[5:]
            elif line.startswith('+++ b/'):
                name = line[6:]
            elif line.startswith('@@ '):
                match = re.search(r'\+(\d+)', line)
                number = int(match[1]) if match else None
            elif scenario['name'].startswith('pr') and number is not None:
                if line.startswith((' ', '+')):
                    shown.setdefault(name, set()).add(number)
                    number += 1
            elif name:
                prefix, sep, _ = line.partition(': ')
                if sep and prefix.isdigit():
                    shown.setdefault(name, set()).add(int(prefix))
    for event in record.get('trace',[]):
        for part in (event.get('content') or {}).get('parts',[]):
            response = part.get('function_response') or {}
            data = response.get('response') or {}
            if response.get('name') == 'read_file' and data.get('path'):
                for line in data.get('content','').splitlines():
                    prefix,sep,_ = line.partition(': ')
                    if sep and prefix.isdigit():
                        shown.setdefault(data['path'],set()).add(int(prefix))
            if response.get('name') == 'search_code':
                for hit in data.get('matches',[]):
                    shown.setdefault(hit['path'],set()).add(hit['line'])
    return shown


def check_evidence(record, info, source):
    checked = []
    visible = visible_lines(record,info)
    for item in record.get('answer',{}).get('evidence',[]):
        valid = False
        try:
            name,start,end,quote = (item[k] for k in ('path','start_line','end_line','quote'))
            lines = source.lines(name)
            valid = (type(start) is int and type(end) is int
                     and 1 <= start <= end <= len(lines)
                     and isinstance(quote,str) and bool(quote.strip())
                     and quote in '\n'.join(lines[start-1:end])
                     and set(range(start,end+1)) <= visible.get(name,set()))
        except (KeyError,TypeError,ValueError):
            pass
        checked.append({'citation':item,'valid_and_seen':valid})
    return checked


def summarize(group=None):
    directory = ROOT / 'runs'
    if group:
        directory /= group
    attempts = range(1, 2 if group else 4)
    manifest=json.loads((ROOT/'manifest.json').read_text())
    audits_path=directory/'audits.json'
    audits=json.loads(audits_path.read_text()) if audits_path.exists() else {}
    rows=[]
    for attempt in attempts:
        for variant,info in manifest['snapshots'].items():
            source=load_source(variant,info)
            for arm in ('single','agent'):
                name=f'{variant}-{arm}-{attempt}'
                path=directory/f'{name}.json'
                r=json.loads(path.read_text()) if path.exists() else {}
                checks=check_evidence(r,info,source)
                expected='vulnerable' if info['vulnerable'] else 'not_vulnerable'
                verdict=r.get('answer',{}).get('verdict')
                audit=audits.get(name,{})
                usage=[u for u in r.get('usage',[]) if u]
                rate_in, rate_out = ((.75, 3.75) if r.get('model') == 'gemini-3.8-flash' else (.3, 2.5))
                tokens_in=sum(u.get('prompt_token_count',0) or 0 for u in usage)
                tokens_out=sum((u.get('candidates_token_count',0) or 0)+
                               (u.get('thoughts_token_count',0) or 0) for u in usage)
                label_correct=(r.get('status')=='completed' and verdict==expected)
                mechanism=audit.get('mechanism_correct')
                grounded=(label_correct and bool(checks) and all(c['valid_and_seen'] for c in checks)
                          and audit.get('all_rubric_items',False))
                rows.append({'run':name,'snapshot':variant,'arm':arm,'attempt':attempt,
                    'status':r.get('status','missing'),'verdict':verdict,
                    'expected':expected,'raw_label_correct':label_correct,
                    'audited_target_correct':bool(label_correct and mechanism),
                    'grounded':grounded,'audit_pending':r.get('status')=='completed' and not audit,
                    'citations':checks,'audit':audit,'calls':r.get('model_calls',0),
                    'seconds':r.get('latency_seconds',0),'input_tokens':tokens_in,
                    'output_tokens':tokens_out,'known_cost_usd':(tokens_in*rate_in+tokens_out*rate_out)/1e6,
                    'unknown_usage_calls':max(0,r.get('model_calls',0)-len(usage))})
    result={'rows':rows,'totals':{}}
    for arm in ('single','agent'):
        subset=[r for r in rows if r['arm']==arm]
        result['totals'][arm]={
            'planned':len(attempts)*2,'completed':sum(r['status']=='completed' for r in subset),
            'raw_labels_correct':sum(r['raw_label_correct'] for r in subset),
            'audited_target_correct':sum(r['audited_target_correct'] for r in subset),
            'grounded':sum(r['grounded'] for r in subset),
            'abstentions':sum(r['verdict']=='insufficient_evidence' for r in subset),
            'false_alarms':sum(r['snapshot']=='b' and r['verdict']=='vulnerable' for r in subset),
            'misses':sum(r['snapshot']=='a' and r['verdict']=='not_vulnerable' for r in subset),
            'pair_successes':sum(all(r['audited_target_correct'] for r in subset if r['attempt']==a)
                                 for a in attempts),
            'model_calls':sum(r['calls'] for r in subset),
            'known_cost_usd':sum(r['known_cost_usd'] for r in subset)}
    (directory/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    print(json.dumps(summarize(sys.argv[1] if len(sys.argv)>1 else None)['totals'],indent=2))
