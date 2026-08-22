#!/usr/bin/env python3
"""Independent Path A: literal HTTP/Memento/WARC reading.
No external project imports, schemas, or implementation dependencies.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def row(case_id: str, result: dict, reason: str, standards: list[str]) -> dict:
    return {
        "case_id": case_id,
        "path": "A_LITERAL_HTTP_MEMENTO_WARC",
        "result": result,
        "reason": reason,
        "standard_used": standards,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    ids = {record["evidence_id"] for record in corpus["evidence_records"]}
    required = {
        "IA-EXAMPLE-2010", "IA-EXAMPLE-2024", "ARQUIVO-EXAMPLE-20100323",
        "IA-EXAMPLE-20100323", "CC-SATURN-20260714", "SUP-ETD-20170706",
    }
    missing = sorted(required - ids)
    if missing:
        raise SystemExit(f"missing required real evidence records: {missing}")

    cases = [
        row(
            "RW-01-ia-same-uri-different-replay",
            {
                "target": "SAME_LITERAL_TARGET_URI",
                "representation": "DIFFERENT_REPLAY_BODY_OBSERVED",
                "time": "ARCHIVE_REPORTED_ORDER_2010_BEFORE_2024",
                "relation": "NO_STANDARD_CAUSAL_RELATION",
                "scope": "LOCAL_HOLDINGS_ONLY",
                "agency": "NOT_STATED_BY_REPLAY",
                "equivocation": "NO_LOG_EVIDENCE",
            },
            "The original URI strings match; replay bodies were observed to differ and archive timestamps order them. HTTP/Memento do not turn those facts into a source-state causal claim.",
            ["RFC 9110", "RFC 7089"],
        ),
        row(
            "RW-02-arquivo-same-digest-multiple-records",
            {
                "target": "SAME_LITERAL_TARGET_URI",
                "representation": "SAME_REPORTED_CDX_DIGEST",
                "time": "MULTIPLE_ARCHIVE_REPORTED_TIMES",
                "relation": "MULTIPLE_INDEX_RECORDS_NO_CAUSAL_LABEL",
                "scope": "LOCAL_INDEX_QUERY_ONLY",
                "agency": "NOT_STATED_BY_CDX",
                "equivocation": "NO_LOG_EVIDENCE",
            },
            "Several returned CDX rows for one literal URI share one digest. CDX/WARC metadata do not define an observation-class relation across rows.",
            ["WARC 1.1", "CDX Server API"],
        ),
        row(
            "RW-03-two-archives-same-uri-same-datetime",
            {
                "target": "SAME_LITERAL_TARGET_URI",
                "representation": "UNVERIFIED_ACROSS_ARCHIVES",
                "time": "EQUAL_REPORTED_DATETIME",
                "relation": "NO_STANDARD_COMMON_EVENT_INFERENCE",
                "scope": "TWO_LOCAL_HOLDINGS",
                "agency": "NO_TRANSFER_EVIDENCE",
                "equivocation": "NO_LOG_EVIDENCE",
            },
            "Two archive endpoints report the same literal URI and 14-digit datetime. RFC 7089 permits multiple servers and does not define a shared-capture-event inference.",
            ["RFC 7089", "Internet Archive Availability API", "Arquivo.pt CDX API"],
        ),
        row(
            "RW-04-commoncrawl-vary-context",
            {
                "target": "ONE_LITERAL_TARGET_URI",
                "representation": "ONE_RECORDED_RESPONSE",
                "time": "ONE_WARC_DATE",
                "relation": "NO_PAIR_TO_CLASSIFY",
                "scope": "ONE_WARC_RECORD",
                "agency": "CRAWLER_FACTS_ONLY",
                "equivocation": "NO_LOG_EVIDENCE",
                "selection_inputs": ["content-language", "Vary", "Cookie", "Authorization", "User-Agent", "GeoIP"],
            },
            "A real WARC response records HTTP selection inputs, but only one response is available. RFC 9110 gives no cross-archive comparison outcome for a missing second request context.",
            ["RFC 9110", "WARC 1.1"],
        ),
        row(
            "RW-05-legacy-wacz-redirect-canonical",
            {
                "target": "LITERAL_URIS_REMAIN_DISTINCT",
                "representation": "REDIRECT_OR_CANONICAL_EVIDENCE_RECORDED",
                "time": "ARCHIVE_LOCAL_CAPTURE_TIME",
                "relation": "NO_TARGET_MERGE_BY_FORMAT",
                "scope": "ONE_PACKAGE_COLLECTION",
                "agency": "PACKAGE_CONTEXT_ONLY",
                "equivocation": "NO_LOG_EVIDENCE",
            },
            "A 301 and canonical link are evidence facts. WARC/WACZ format rules do not specify that arbitrary redirect/canonical forms are one logical target across archives.",
            ["RFC 9110", "WARC 1.1", "WACZ 1.1.1"],
        ),
        row(
            "RW-06-ukwa-query-blocked",
            {
                "target": "NO_CAPTURE_RESULT",
                "representation": "NO_CAPTURE_RESULT",
                "time": "NO_CAPTURE_RESULT",
                "relation": "UNAVAILABLE_FOR_AUTOMATED_COLLECTION",
                "scope": "NO_SCOPE_ASSERTION",
                "agency": "NO_CAPTURE_RESULT",
                "equivocation": "NO_CAPTURE_RESULT",
            },
            "A human-verification page blocked the query. Non-return cannot be read as archive or historical absence.",
            ["Observed public access result"],
        ),
        row(
            "RW-07-import-and-checkpoint",
            {
                "target": "NO_CASE_EVIDENCE",
                "representation": "NO_CASE_EVIDENCE",
                "time": "NO_CASE_EVIDENCE",
                "relation": "NO_CASE_EVIDENCE",
                "scope": "NO_CASE_EVIDENCE",
                "agency": "NO_PROVENANCE_TRANSFER",
                "equivocation": "NO_SIGNED_TREE_HEAD_PAIR",
            },
            "The corpus contains no archive-to-archive transfer proof and no two checkpoint artifacts. Generic standards cannot supply missing facts.",
            ["PROV-DM", "VC 2.0", "RFC 9943", "RFC 9162"],
        ),
    ]
    Path(args.output).write_text(json.dumps({"corpus_version": corpus["registry_version"], "cases": cases}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
