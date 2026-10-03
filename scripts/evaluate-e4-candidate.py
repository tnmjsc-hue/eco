"""Evaluate the E4 candidate descriptively against a frozen Core snapshot."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eco.core import compute
from eco.extended import compute_fee_activity, evaluate_fee_activity


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("core_canonical")
    parser.add_argument("fee_canonical")
    parser.add_argument("--output")
    args = parser.parse_args()
    core_source = read_jsonl(args.core_canonical)
    fee_source = read_jsonl(args.fee_canonical)
    core = compute(core_source)
    fee = compute_fee_activity(fee_source)
    result = evaluate_fee_activity(core, fee)
    encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    print(json.dumps({"status": result["status"], "n": result["n"],
                      "start": result["start"], "end": result["end"],
                      "positive_labels": result["positive_labels"],
                      "decision": result["decision"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
