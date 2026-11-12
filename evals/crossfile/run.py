"""Frozen single-function versus repository-agent comparison, 12 attempts."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

from google.adk.agents import Agent
from google.adk.agents.run_config import RunConfig
from google.adk.runners import InMemoryRunner
from google.genai import types

from agent import make_agent
from evals.run import Budget, MODEL, digest
from tools import RepositoryTools
from tools import _source

ROOT = Path(__file__).parent


def load_source(variant, info):
    # Eval-only C corpus profile. Production CLI/web limits are unchanged.
    previous = (_source.EXTENSIONS, _source.MAX_FILE, _source.MAX_TOTAL)
    try:
        _source.EXTENSIONS = {'.c', '.h'}
        _source.MAX_FILE = 512_000
        _source.MAX_TOTAL = 3_000_000
        source = RepositoryTools(ROOT / 'fixtures' / variant)
    finally:
        (_source.EXTENSIONS, _source.MAX_FILE, _source.MAX_TOTAL) = previous
    if source.omitted or set(source.files) != set(info['files']):
        raise ValueError('Source profile omitted files')
    for name, hashes in info['files'].items():
        if hashlib.sha256(source.files[name].encode()).hexdigest() != hashes['sha256']:
            raise ValueError('Source changed since manifest freeze')
    return source


def parse_answer(answer):
    value = json.loads(answer)
    if set(value) != {'verdict', 'explanation', 'evidence', 'limitations'}:
        raise ValueError('Wrong answer fields')
    if value['verdict'] not in ('vulnerable', 'not_vulnerable', 'insufficient_evidence'):
        raise ValueError('Wrong verdict')
    if not all(isinstance(value[k], str) and value[k].strip()
               for k in ('explanation', 'limitations')):
        raise ValueError('Missing prose')
    if not isinstance(value['evidence'], list):
        raise ValueError('Missing evidence list')
    return value


async def run_one(variant, arm, attempt, manifest, budget, phase2=False, scenario=None):
    directory = ROOT / ('runs/' + scenario['name'] if scenario
                        else 'runs/phase2' if phase2 else 'runs')
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{variant}-{arm}-{attempt}.json'
    if path.exists():
        return
    info = manifest['snapshots'][variant]
    source = load_source(variant, info)
    max_calls = (12 if phase2 else 8) if arm == 'agent' else 1
    key = os.environ['GEMINI_API_KEY']
    model = scenario.get('model', MODEL) if scenario else MODEL
    agent = make_agent(source, model, key)
    if model == 'gemini-3.8-flash':
        agent.generate_content_config.response_mime_type = 'application/json'
        agent.generate_content_config.max_output_tokens = 4000
    agent.instruction = (scenario.get('instruction_override') if scenario else None) or (ROOT / 'prompt.txt').read_text()
    agent.instruction += f'\nYou have at most {max_calls} model calls. Finish within this limit.'
    if arm == 'single':
        agent.tools = []
    else:
        agent.instruction += '\nUse search_code and read_file to inspect relevant repository context.'
    if phase2:
        agent.instruction += (ROOT / 'phase2-format.txt').read_text()
        if arm == 'agent':
            agent.instruction += (ROOT / 'phase2-investigation.txt').read_text()
    lines = source.lines(info['focal_path'])
    question = 'Review the following function.\nFILE '+info['focal_path']+'\n'
    question += '\n'.join(f'{n}: {lines[n-1]}' for n in
                          range(info['start_line'], info['end_line']+1))
    if scenario:
        question = scenario['question']
        agent.instruction += scenario['instruction']
    record = {'snapshot': variant, 'arm': arm, 'attempt': attempt,
              'model': model, 'started_at': datetime.now(timezone.utc).isoformat(),
              'instruction': agent.instruction, 'question': question,
              'manifest_sha256': (scenario.get('manifest_sha256') if scenario else None) or digest(ROOT / 'manifest.json'),
              'protocol_sha256': digest(ROOT / ('WHOLE-REPO.md' if scenario and scenario['name'].startswith('whole-repo') else
                  'SCENARIOS.md' if scenario else
                  'PHASE2.md' if phase2 else 'PROTOCOL.md')),
              'scenario': scenario,
              'max_model_calls': max_calls, 'status': 'started', 'trace': [],
              'usage': [], 'model_calls': 0}
    async def before_model(callback_context, llm_request):
        if record['model_calls'] >= max_calls:
            raise RuntimeError('Call limit')
        wire_bytes = len(llm_request.model_dump_json(exclude={'tools_dict'}).encode())
        limit = 256_000 if scenario else 80_000
        if wire_bytes > limit:
            raise RuntimeError('Request size limit')
        if scenario:
            cumulative = record.get('input_serialized_bytes', 0) + wire_bytes
            if cumulative > limit:
                raise RuntimeError('Cumulative input byte budget')
            record['input_serialized_bytes'] = cumulative
        await asyncio.sleep(max(0, budget.data.get('last_request_at',0)+4.5-time.time()))
        extra = 0.20 if model == 'gemini-3.8-flash' else 0
        if budget.data['estimated_usd'] + extra + 0.05 > budget.cap:
            raise RuntimeError('Aggregate cost cap reached')
        budget.data['estimated_usd'] += extra
        budget.reserve()
        budget.data['last_request_at'] = time.time()
        budget.save()
        record['model_calls'] += 1
    def after_model(callback_context, llm_response):
        usage = llm_response.usage_metadata
        budget.settle(usage)
        if model == 'gemini-3.8-flash' and usage and usage.prompt_token_count is not None and usage.candidates_token_count is not None:
            extra_cost = (usage.prompt_token_count * .45 +
                (usage.candidates_token_count + (usage.thoughts_token_count or 0)) * 1.25) / 1e6
            budget.data['estimated_usd'] += extra_cost - .20
            budget.save()
        record['usage'].append(usage.model_dump(mode='json') if usage else None)
    agent.before_model_callback = before_model
    agent.after_model_callback = after_model
    budget.data['attempts'] += 1
    budget.save()
    path.write_text(json.dumps(record, indent=2))
    runner = InMemoryRunner(agent=agent, app_name='crossfile_review')
    start = time.monotonic()
    try:
        session = await runner.session_service.create_session(
            app_name='crossfile_review', user_id='reviewer')
        async with asyncio.timeout(240 if phase2 else 120):
            events = runner.run_async(user_id='reviewer', session_id=session.id,
                new_message=types.Content(role='user',parts=[types.Part.from_text(text=question)]),
                run_config=RunConfig(max_llm_calls=max_calls))
            try:
                async for event in events:
                    record['trace'].append(event.model_dump(mode='json',exclude_none=True))
                    if event.error_code:
                        raise RuntimeError('Provider event error')
                    if event.is_final_response() and event.content:
                        answer = '\n'.join(p.text for p in event.content.parts or []
                                           if p.text and not p.thought).strip()
                        if answer:
                            record['answer_text'] = answer
                            record['answer'] = parse_answer(answer)
                            record['status'] = 'completed'
                            break
            finally:
                await events.aclose()
        if record['status'] == 'started':
            record['status'] = 'incomplete'
    except Exception as exc:
        record['status'] = 'incomplete'
        record['error'] = type(exc).__name__
    finally:
        await runner.close()
    record['latency_seconds'] = round(time.monotonic()-start,3)
    path.write_text(json.dumps(record,indent=2)+'\n')
    print(path.name,record['status'],record.get('answer',{}).get('verdict'),
          record['model_calls'],flush=True)


async def main():
    manifest = json.loads((ROOT/'manifest.json').read_text())
    # Carry forward earlier cost accounting; total cap remains $5.
    ledger = ROOT/'runs/budget.json'
    ledger.parent.mkdir(parents=True,exist_ok=True)
    if not ledger.exists():
        prior = json.loads((ROOT.parent/'runs/budget.json').read_text())
        ledger.write_text(json.dumps({'estimated_usd':prior['estimated_usd'],
             'prior_estimated_usd':prior['estimated_usd'], 'attempts':0,'calls_reserved':0}))
    budget = Budget(ledger, 1.00)  # A stricter combined cap than the approved $5.
    for attempt in range(1,4):
        for variant in (('a','b') if attempt%2 else ('b','a')):
            arms = ('single','agent') if (attempt+(variant=='b'))%2 else ('agent','single')
            for arm in arms:
                if budget.data['attempts'] >= 12:
                    return
                await run_one(variant,arm,attempt,manifest,budget)


if __name__ == '__main__':
    asyncio.run(main())
