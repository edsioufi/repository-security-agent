"""Score target CWEs only, with explicit manual audits for claimed positives."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).parent


def classify(case, run, audit):
    if run is None or run.get("status") != "accepted":
        return "incomplete"
    matching = [f for f in run["report"]["findings"]
                if f["cwe"] == case["category"] and f["path"] == "app.py"]
    predicted = bool(matching)
    if predicted and audit is None:
        return "pending_audit"
    supported = predicted and audit["valid_target_finding"]
    if case["vulnerable"]:
        return "TP" if supported else "FN"
    return "FP" if predicted else "TN"


def summarize(batch, attempts=2):
    cases = json.loads((ROOT / "manifest.json").read_text())["cases"]
    audits_path = batch / "audits.json"
    audits = json.loads(audits_path.read_text()) if audits_path.exists() else {}
    totals = defaultdict(lambda: defaultdict(int))
    rows = []
    for case in cases:
        for arm in ("baseline", "context", "single"):
            count = attempts if case["split"] == "holdout" and arm != "single" else 1
            for attempt in range(1, count + 1):
                name = f'{case["id"]}-{arm}-{attempt}'
                path = batch / (name + ".json")
                run = json.loads(path.read_text()) if path.exists() else None
                outcome = classify(case, run, audits.get(name))
                key = case["split"] + "/" + arm
                totals[key][outcome] += 1
                other = sum(
                    f["cwe"] != case["category"] or f["path"] != "app.py"
                    for f in (run or {}).get("report", {}).get("findings", [])
                ) if run and run.get("report") else 0
                row = dict(case=case["id"], split=case["split"], arm=arm,
                           attempt=attempt, expected=case["vulnerable"],
                           cwe=case["category"], outcome=outcome,
                           other_findings=other)
                if run:
                    row.update(model_calls=min(run.get("model_calls", 0), run.get("max_model_calls", 8)),
                               seconds=run.get("latency_seconds", 0))
                if run:
                    usages = [u for u in run.get("usage", []) if u]
                    row["input_tokens"] = sum(u.get("prompt_token_count") or 0 for u in usages)
                    row["output_tokens"] = sum((u.get("candidates_token_count") or 0)
                                              + (u.get("thoughts_token_count") or 0)
                                              for u in usages)
                    row["unknown_usage_calls"] = max(
                        0, row["model_calls"] - len(usages))
                    row["tool_calls"] = sum(
                        bool(p.get("function_call"))
                        for e in run.get("trace", [])
                        for p in (e.get("content") or {}).get("parts", []))
                rows.append(row)
    metrics = {}
    for group, counts in totals.items():
        selected = [r for r in rows if r["split"] + "/" + r["arm"] == group]
        tp, fp, fn, tn = [counts.get(k, 0) for k in ("TP", "FP", "FN", "TN")]
        positive = sum(r["expected"] for r in selected)
        inp = sum(r.get("input_tokens", 0) for r in selected)
        out = sum(r.get("output_tokens", 0) for r in selected)
        metrics[group] = {
            "planned": len(selected), "correct_target_decisions": tp + tn,
            "completed": tp + fp + fn + tn,
            "precision_completed": tp / (tp + fp) if tp + fp else None,
            "recall_completed": tp / (tp + fn) if tp + fn else None,
            "detected_per_planned_positive": tp / positive if positive else None,
            "model_calls": sum(r.get("model_calls", 0) for r in selected),
            "tool_calls": sum(r.get("tool_calls", 0) for r in selected),
            "latency_seconds": round(sum(r.get("seconds", 0) for r in selected), 3),
            "input_tokens": inp, "output_tokens_including_thoughts": out,
            "known_usage_estimated_usd": (inp * .30 + out * 2.50) / 1_000_000,
            "unknown_usage_calls": sum(r.get("unknown_usage_calls", 0) for r in selected),
            "other_findings": sum(r["other_findings"] for r in selected),
        }
    summary = {"totals": dict(totals), "metrics": metrics, "rows": rows}
    (batch / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["totals"], indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--attempts", type=int, default=2)
    args = parser.parse_args()
    summarize(args.batch, args.attempts)
