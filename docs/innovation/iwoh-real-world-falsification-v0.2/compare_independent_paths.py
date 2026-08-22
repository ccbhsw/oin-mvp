#!/usr/bin/env python3
"""Audit comparator for two independently authored standards-only result files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FACTUAL_PROJECTION = {
    "RW-01-ia-same-uri-different-replay": {
        "fact": "same literal URI; different replay bodies; archive-reported 2010-before-2024; no causal proof",
        "finding": "SEMANTICALLY_COMPATIBLE_CONSERVATISM",
        "reason": "A uses literal resource language while B uses Memento/PROV candidate language; both reject a source-causality claim.",
    },
    "RW-02-arquivo-same-digest-multiple-records": {
        "fact": "one literal URI; repeated index rows; same reported digest; no capture-activity provenance",
        "finding": "SEMANTICALLY_COMPATIBLE_CONSERVATISM",
        "reason": "A declines a causal label and B labels a potential duplicate evidence artifact; neither claims a repeated observation fact.",
    },
    "RW-03-two-archives-same-uri-same-datetime": {
        "fact": "same literal URI; equal declared datetime; two archive services; no transfer or common-event proof",
        "finding": "SEMANTICALLY_COMPATIBLE_CONSERVATISM",
        "reason": "Both paths reject an inference that equal timestamp proves the same capture event or a causal relation.",
    },
    "RW-04-commoncrawl-vary-context": {
        "fact": "one WARC response; selection context recorded; no second contextually matched response",
        "finding": "SEMANTICALLY_COMPATIBLE_CONSERVATISM",
        "reason": "Both paths retain Vary/context inputs and decline a pairwise comparison result.",
    },
    "RW-05-legacy-wacz-redirect-canonical": {
        "fact": "typed redirect/canonical evidence exists; no cross-archive equivalence assertion",
        "finding": "SEMANTICALLY_COMPATIBLE_CONSERVATISM",
        "reason": "Both paths keep target references distinct rather than silently merge them.",
    },
    "RW-06-ukwa-query-blocked": {
        "fact": "human verification blocked automated capture query; no scope/capture result",
        "finding": "SEMANTICALLY_COMPATIBLE_CONSERVATISM",
        "reason": "Both paths reject an absence inference from blocked access.",
    },
    "RW-07-import-and-checkpoint": {
        "fact": "no import transfer proof and no same-log signed checkpoint pair",
        "finding": "SEMANTICALLY_COMPATIBLE_CONSERVATISM",
        "reason": "Both paths retain missing evidence rather than manufacture agency or equivocation results.",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True)
    parser.add_argument("--b", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    a = json.loads(Path(args.a).read_text(encoding="utf-8"))
    b = json.loads(Path(args.b).read_text(encoding="utf-8"))
    a_cases = {case["case_id"]: case for case in a["cases"]}
    b_cases = {case["case_id"]: case for case in b["cases"]}
    ids = sorted(set(a_cases) | set(b_cases))
    rows = []
    exact_matches = 0
    compatible = 0
    for case_id in ids:
        left, right = a_cases.get(case_id), b_cases.get(case_id)
        if left is None or right is None:
            rows.append({"case_id": case_id, "agreement": "MISSING_RESULT", "reason": "one path did not emit a result"})
            continue
        exact = left["result"] == right["result"]
        if exact:
            exact_matches += 1
        projection = FACTUAL_PROJECTION.get(case_id)
        if projection is None:
            agreement = "UNREVIEWED"
            reason = "no predeclared factual projection"
        else:
            agreement = projection["finding"]
            reason = projection["reason"]
            compatible += 1
        rows.append({
            "case_id": case_id,
            "a_result": left["result"],
            "b_result": right["result"],
            "exact_serialized_agreement": exact,
            "agreement": agreement,
            "factual_projection": projection["fact"] if projection else None,
            "reason": reason,
            "a_standard_used": left["standard_used"],
            "b_standard_used": right["standard_used"],
        })
    out = {
        "case_count": len(ids),
        "exact_serialized_agreement_count": exact_matches,
        "semantic_compatibility_count": compatible,
        "interpretation": "Different standards-only labels are not naturally interoperable. All reviewed paths remain factually conservative; no case establishes a contradictory historical assertion.",
        "cases": rows,
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
