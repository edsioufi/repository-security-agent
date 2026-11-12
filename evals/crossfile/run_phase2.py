"""Four exploratory attempts; frozen pilot files remain untouched."""
import asyncio
import json
from evals.crossfile.run import ROOT, run_one
from evals.run import Budget


async def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    budget = Budget(ROOT / 'runs/budget.json', 1.00)
    for variant, arm in [('a', 'single'), ('a', 'agent'),
                         ('b', 'agent'), ('b', 'single')]:
        await run_one(variant, arm, 1, manifest, budget, phase2=True)


if __name__ == '__main__':
    asyncio.run(main())
