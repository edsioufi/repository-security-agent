"""Prepare source-only fixtures without importing or executing target code."""
import argparse
import ast
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import tokenize

PIN = "f1291485808b66e20ddb6b01b10dc71b3df8c8ba"
ROOT = Path(__file__).parent
# Fixed before any model runs; distinct flows/sinks across each category split.
SELECTION = [
    ("dev", 99), ("dev", 11), ("dev", 165), ("dev", 350),
    ("dev", 1), ("dev", 4),
    ("holdout", 454), ("holdout", 755), ("holdout", 899),
    ("holdout", 1097), ("holdout", 87), ("holdout", 88),
]
CATEGORIES = {"sqli": "CWE-89", "cmdi": "CWE-78", "pathtraver": "CWE-22"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sanitize(text):
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    # Preserve line numbers while removing identifying module prose/comments.
    if tree.body and isinstance(tree.body[0], ast.Expr):
        node = tree.body[0]
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for i in range(node.lineno - 1, node.end_lineno):
                lines[i] = "\n"
    text = "".join(lines)
    for token in reversed(list(tokenize.generate_tokens(io.StringIO(text).readline))):
        if token.type == tokenize.COMMENT:
            row, col = token.start
            lines[row - 1] = lines[row - 1][:col] + "\n"
    text = "".join(lines)
    text = re.sub(r"BenchmarkTest\d+", "endpoint", text)
    text = re.sub(r"(sqli|cmdi|pathtraver)-\d+", "review", text)
    text = text.replace("Problem executing cmdi", "Problem executing command")
    ast.parse(text)
    return text


def prepare(source):
    rows = list(csv.reader((source / "expectedresults-0.1.csv").read_text().splitlines()[1:]))
    labels = {r[0]: r for r in rows}
    pinned = json.loads((ROOT / "manifest.json").read_text())
    if sha((source / "expectedresults-0.1.csv").read_bytes()) != pinned["labels_sha256"]:
        raise ValueError("Labels differ from pinned source")
    expected_hashes = {v["upstream_path"]: v["upstream_sha256"]
                       for c in pinned["cases"]
                       for v in c["provenance"].values()}
    cases = []
    for number, (split, identifier) in enumerate(SELECTION, 1):
        name = f"BenchmarkTest{identifier:05}"
        label = labels[name]
        entry = source / "testcode" / (name + ".py")
        # Transitive helper imports are followed statically, never imported.
        pending = [entry]
        selected = {}
        while pending:
            path = pending.pop()
            relative = path.relative_to(source).as_posix()
            if relative in selected:
                continue
            raw = path.read_bytes()
            if sha(raw) != expected_hashes.get(relative):
                raise ValueError("Source differs from pinned commit: " + relative)
            selected[relative] = raw
            for helper in re.findall(r"(?:import|from) (helpers\.[a-zA-Z_]+)", raw.decode()):
                target = source / (helper.replace(".", "/") + ".py")
                if target.exists():
                    pending.append(target)
        case_id = f"case-{number:02}"
        destination = ROOT / "fixtures" / case_id
        hashes = {}
        mappings = {}
        for relative, raw in selected.items():
            output = "app.py" if relative.startswith("testcode/") else relative
            target = destination / output
            target.parent.mkdir(parents=True, exist_ok=True)
            cleaned = sanitize(raw.decode())
            target.write_text(cleaned)
            hashes[output] = sha(cleaned.encode())
            mappings[output] = {
                "upstream_path": relative, "upstream_sha256": sha(raw),
                "line_mapping": "identity",
            }
        cases.append({
            "id": case_id, "split": split, "upstream": name,
            "category": CATEGORIES[label[1]], "vulnerable": label[2] == "true",
            "files": hashes, "provenance": mappings,
        })
    manifest = {"commit": PIN, "source": "https://github.com/OWASP-Benchmark/BenchmarkPython",
                "labels_sha256": sha((source / "expectedresults-0.1.csv").read_bytes()),
                "transformations": [
                    "Blank module header and comments; preserve line numbers",
                    "Rename benchmark identifiers to endpoint",
                    "Neutralize category-bearing route/template names and error text",
                    "No data-flow or sink expressions changed",
                ], "cases": cases}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "UPSTREAM-LICENSE.txt").write_bytes((source / "LICENSE").read_bytes())
    print(f"Prepared {len(cases)} fixtures; labels stay outside snapshots.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    prepare(parser.parse_args().source)
