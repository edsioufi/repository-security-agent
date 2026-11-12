"""Explicit large-repository and diff-only development experiments."""
import asyncio
import difflib
import json
import re
from evals.crossfile.run import ROOT, load_source, run_one
from evals.run import Budget


def build(variant, arm, kind, manifest):
    info = manifest['snapshots'][variant]
    source = load_source(variant, info)
    focal = info['focal_path']
    lines = source.lines(focal)
    seed = '\n'.join(lines[info['start_line']-1:info['end_line']])
    inventory = '\n'.join(sorted(source.files))
    if kind == 'large':
        question = 'Review this entry point within the repository.\n'
        question += f'FILE {focal}\n' + '\n'.join(
            f'{i}: {lines[i-1]}' for i in
            range(info['start_line'], info['end_line']+1))
        question += '\nREPOSITORY FILES\n' + inventory
        included = []
        if arm == 'single':
            for name in sorted(source.files):
                question += '\nFILE '+name+'\n'+'\n'.join(
                    f'{i}: {s}' for i,s in enumerate(source.lines(name),1))
                included.append(name)
        return {'name': kind, 'question': question,
                'instruction': '\nAssess only the specified entry point.',
                'included_files': included,
                'repository_bytes': sum(len(v.encode()) for v in source.files.values()),
                'repository_files': len(source.files)}
    other = 'a' if variant == 'b' else 'b'
    before = load_source(other, manifest['snapshots'][other])
    diff = ''.join(difflib.unified_diff(
        before.files[focal].splitlines(keepends=True),
        source.files[focal].splitlines(keepends=True),
        fromfile='a/'+focal, tofile='b/'+focal, n=3))
    return {'name':kind,
            'question': 'Review the resulting capture-source behavior after this '
                        'patch. Determine whether it permits client-selected '
                        'remote capture connections.\n'+diff,
            'instruction': '\nFor this task the supplied evidence is a patch. '
                           'Tools, when available, read its resulting tree. '
                           'Other relevant implementations are unchanged.',
            'patch_kind': 'upstream fix' if variant == 'b' else
                          'synthetic reversal of upstream fix (regression)',
            'changed_files': [focal]}


async def main():
    manifest = json.loads((ROOT/'manifest.json').read_text())
    budget = Budget(ROOT/'runs/budget.json', 5.00)
    for kind in ('pr',):
        for variant in ('a', 'b'):
            for arm in ('single', 'agent'):
                config = build(variant, arm, kind, manifest)
                config['name'] = 'pr-current'
                config['model'] = 'gemini-3.8-flash'
                await run_one(variant, arm, 1, manifest, budget,
                              phase2=True, scenario=config)


if __name__ == '__main__':
    asyncio.run(main())
