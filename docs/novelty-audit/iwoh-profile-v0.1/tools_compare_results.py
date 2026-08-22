#!/usr/bin/env python3
"""Compare IWOH implementation outputs against the static corpus assertions.

This tool is intentionally outside implementations A and B. It only compares
serialized result contracts; it contains no target, archive, time or provenance
rule and therefore cannot supply verifier decision logic.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

FIELDS = [
    "target_identity", "target_relation", "statement_validity", "comparability",
    "relationship", "history_membership", "completeness_scope",
    "statement_import_validity", "equivocation_status",
]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(label: str, actual: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if actual.get("profile_version") != expected.get("profile_version"):
        failures.append({"implementation": label, "kind": "profile_version", "actual": actual.get("profile_version"), "expected": expected.get("profile_version")})
    actual_results = actual.get("results", {})
    expected_results = expected.get("scenarios", {})
    if set(actual_results) != set(expected_results):
        failures.append({"implementation": label, "kind": "scenario_set", "actual": sorted(actual_results), "expected": sorted(expected_results)})
    for scenario_id in sorted(set(actual_results) | set(expected_results)):
        actual_scenario = actual_results.get(scenario_id, {})
        expected_scenario = expected_results.get(scenario_id, {})
        for field in FIELDS:
            if actual_scenario.get(field) != expected_scenario.get(field):
                failures.append({"implementation": label, "scenario": scenario_id, "field": field, "actual": actual_scenario.get(field), "expected": expected_scenario.get(field)})
    return failures


def pairwise(left_label: str, left: dict[str, Any], right_label: str, right: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    left_results, right_results = left.get("results", {}), right.get("results", {})
    for scenario_id in sorted(set(left_results) | set(right_results)):
        for field in FIELDS:
            left_value = left_results.get(scenario_id, {}).get(field)
            right_value = right_results.get(scenario_id, {}).get(field)
            if left_value != right_value:
                failures.append({"implementation": f"{left_label} vs {right_label}", "scenario": scenario_id, "field": field, "left": left_value, "right": right_value})
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--result", type=Path, action="append", required=True, help="One or more verifier output JSON files")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    expected = load(args.expected)
    results = [(path.stem, load(path)) for path in args.result]
    failures = []
    for label, document in results:
        failures.extend(compare(label, document, expected))
    if len(results) >= 2:
        for index, (left_label, left_doc) in enumerate(results):
            for right_label, right_doc in results[index + 1:]:
                failures.extend(pairwise(left_label, left_doc, right_label, right_doc))
    report = {
        "profile_version": expected.get("profile_version"),
        "assertion_fields": FIELDS,
        "result_files": [str(path) for path in args.result],
        "expected_file": str(args.expected),
        "pass": not failures,
        "failure_count": len(failures),
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"comparison_pass={str(not failures).lower()} failures={len(failures)} output={args.output}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
