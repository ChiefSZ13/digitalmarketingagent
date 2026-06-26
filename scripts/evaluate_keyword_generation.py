from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from marketing_agent.domain.models.evidence import (
    EvidenceLinkedText,
    EvidenceRecord,
    EvidenceSource,
)
from marketing_agent.domain.models.product import ProductProfile
from marketing_agent.domain.services.keyword_generator import generate_keyword_candidates
from marketing_agent.domain.services.keyword_normalizer import normalize_keyword
from marketing_agent.domain.services.search_query_validator import SearchQueryValidator


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cases = json.loads(
        (root / "tests" / "evals" / "keyword_generation_cases.json").read_text(
            encoding="utf-8"
        )
    )
    results: list[dict[str, Any]] = []
    all_queries: list[str] = []
    family_counts: dict[str, int] = {}
    rejected_bad_queries = 0
    description_copy_rejections = 0
    bad_query_count = 0

    for case in cases:
        profile = _profile(case)
        generated = generate_keyword_candidates(profile)
        generated_texts = [candidate.normalized_text for candidate in generated]
        all_queries.extend(generated_texts)
        for candidate in generated:
            family_counts[candidate.query_family.value] = (
                family_counts.get(candidate.query_family.value, 0) + 1
            )

        validator = SearchQueryValidator(profile)
        bad_results = [validator.validate(query) for query in case["bad_queries"]]
        bad_query_count += len(bad_results)
        rejected_bad_queries += sum(
            1 for result in bad_results if not result.eligible_for_live_enrichment
        )
        description_copy_rejections += sum(
            1
            for result in bad_results
            if "description_copy" in {reason.value for reason in result.rejection_reasons}
        )

        expected = {normalize_keyword(value) for value in case["expected_any"]}
        matched_expected = sorted(expected.intersection(generated_texts))
        results.append(
            {
                "name": case["name"],
                "query_count": len(generated),
                "matched_expected": matched_expected,
                "max_word_count": max((len(query.split()) for query in generated_texts), default=0),
                "bad_queries_rejected": [
                    not result.eligible_for_live_enrichment for result in bad_results
                ],
                "passed": bool(matched_expected)
                and all(not result.eligible_for_live_enrichment for result in bad_results)
                and all(2 <= len(query.split()) <= 10 for query in generated_texts),
            }
        )

    word_counts = [len(query.split()) for query in all_queries]
    unique_count = len(set(all_queries))
    duplicate_rate = 1 - unique_count / max(len(all_queries), 1)
    metrics = {
        "case_count": len(cases),
        "generated_query_count": len(all_queries),
        "average_word_count": round(statistics.mean(word_counts), 3) if word_counts else 0,
        "median_word_count": statistics.median(word_counts) if word_counts else 0,
        "max_word_count": max(word_counts, default=0),
        "percent_over_8_words": round(
            sum(1 for count in word_counts if count > 8) / max(len(word_counts), 1),
            3,
        ),
        "percent_over_10_words": round(
            sum(1 for count in word_counts if count > 10) / max(len(word_counts), 1),
            3,
        ),
        "duplicate_rate": round(duplicate_rate, 3),
        "expected_query_recall": round(
            sum(1 for result in results if result["matched_expected"]) / max(len(results), 1),
            3,
        ),
        "bad_query_rejection_rate": round(
            rejected_bad_queries / max(bad_query_count, 1),
            3,
        ),
        "description_copy_rejection_count": description_copy_rejections,
        "family_counts": family_counts,
        "dataset_limitation": (
            "Small hand-authored smoke set for query realism; not a market demand benchmark."
        ),
    }
    report = {
        "metrics": metrics,
        "failures": [result for result in results if not result["passed"]],
    }
    print(json.dumps(report, indent=2))
    if report["failures"]:
        raise SystemExit("Keyword generation evaluation failed.")
    if metrics["percent_over_10_words"] > 0:
        raise SystemExit("Generated query exceeded absolute 10-word limit.")
    if metrics["duplicate_rate"] > 0.05:
        raise SystemExit("Duplicate rate above 5%.")
    if metrics["bad_query_rejection_rate"] < 0.95:
        raise SystemExit("Bad query rejection rate below 95%.")


def _profile(case: dict[str, Any]) -> ProductProfile:
    evidence = [
        EvidenceRecord(
            id="ev-description-1",
            source=EvidenceSource.USER_DESCRIPTION,
            source_reference="description",
            observation="Fixture product description",
            quote=case["description"],
            confidence=0.95,
        ),
        EvidenceRecord(
            id="ev-inference-1",
            source=EvidenceSource.MODEL_INFERENCE,
            source_reference="keyword_generation_eval",
            observation="Fixture normalized product profile",
            confidence=0.8,
        ),
    ]
    if case.get("brand"):
        evidence.append(
            EvidenceRecord(
                id="ev-brand-1",
                source=EvidenceSource.USER_METADATA,
                source_reference="brand",
                observation="Fixture brand",
                quote=case["brand"],
                confidence=0.95,
            )
        )
    description_ids = ["ev-description-1"]
    product_ids = ["ev-description-1", "ev-inference-1"]
    return ProductProfile(
        product_name=EvidenceLinkedText(
            value=case["product_name"], evidence_ids=product_ids, confidence=0.9
        ),
        brand=(
            EvidenceLinkedText(value=case["brand"], evidence_ids=["ev-brand-1"], confidence=0.95)
            if case.get("brand")
            else None
        ),
        category=EvidenceLinkedText(
            value=case["category"], evidence_ids=product_ids, confidence=0.85
        ),
        marketplace_search_query=EvidenceLinkedText(
            value=case["product_name"], evidence_ids=product_ids, confidence=0.85
        ),
        summary=EvidenceLinkedText(
            value=case["description"], evidence_ids=description_ids, confidence=0.85
        ),
        user_provided_facts=[
            EvidenceLinkedText(
                value=case["description"],
                evidence_ids=description_ids,
                confidence=0.95,
            )
        ],
        features=[
            EvidenceLinkedText(value=value, evidence_ids=description_ids, confidence=0.8)
            for value in case["features"]
        ],
        benefits=[
            EvidenceLinkedText(value=value, evidence_ids=description_ids, confidence=0.75)
            for value in case["benefits"]
        ],
        use_cases=[
            EvidenceLinkedText(value=value, evidence_ids=description_ids, confidence=0.75)
            for value in case["use_cases"]
        ],
        unknowns=[
            EvidenceLinkedText(
                value="No live keyword metrics in MVP 1B.",
                evidence_ids=["ev-inference-1"],
                confidence=1.0,
            )
        ],
        evidence=evidence,
        overall_confidence=0.84,
    )


if __name__ == "__main__":
    main()
