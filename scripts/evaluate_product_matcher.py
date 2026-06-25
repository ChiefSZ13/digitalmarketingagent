from __future__ import annotations

import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from marketing_agent.domain.models.evidence import EvidenceRecord, EvidenceSource
from marketing_agent.domain.models.marketplace import (
    NormalizedMarketplaceListing,
    ProductCondition,
    ProductIdentity,
    ProductMatchStatus,
    RankSignal,
)
from marketing_agent.domain.services.product_matcher import (
    decimal_or_none,
    extract_model_number,
    match_listing,
    normalize_text,
    parse_condition,
    parse_package,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cases = json.loads(
        (root / "tests" / "evals" / "product_matcher_cases.json").read_text(encoding="utf-8")
    )
    results: list[dict[str, Any]] = []
    latencies_ms: list[float] = []

    for case in cases:
        product = _identity(case["product"])
        listing = _listing(case["listing"])
        started = time.perf_counter()
        result = match_listing(product, listing)
        latencies_ms.append((time.perf_counter() - started) * 1000)
        conflicts = [conflict.code for conflict in result.conflicts]
        expected_conflicts = case["expected_conflicts"]
        results.append(
            {
                "name": case["name"],
                "expected_status": case["expected_status"],
                "actual_status": result.status.value,
                "expected_conflicts": expected_conflicts,
                "actual_conflicts": conflicts,
                "expected_eligible": case["eligible_for_price_aggregation"],
                "actual_eligible": result.eligible_for_price_aggregation,
                "expected_group": case["expected_aggregation_group"],
                "actual_group": result.aggregation_group,
                "passed": (
                    result.status.value == case["expected_status"]
                    and set(expected_conflicts).issubset(conflicts)
                    and result.eligible_for_price_aggregation
                    == case["eligible_for_price_aggregation"]
                    and result.aggregation_group == case["expected_aggregation_group"]
                ),
            }
        )

    accepted_expected = {
        item["name"]
        for item in results
        if item["expected_status"] in {"exact_match", "probable_match"}
    }
    accepted_actual = {
        item["name"] for item in results if item["actual_status"] in {"exact_match", "probable_match"}
    }
    false_confident = accepted_actual.difference(accepted_expected)
    false_rejections = {
        item["name"]
        for item in results
        if item["expected_status"] in {"exact_match", "probable_match"}
        and item["actual_status"] == "rejected"
    }
    accepted_precision = (
        len(accepted_actual.intersection(accepted_expected)) / len(accepted_actual)
        if accepted_actual
        else 0.0
    )
    recall = (
        len(accepted_actual.intersection(accepted_expected)) / len(accepted_expected)
        if accepted_expected
        else 0.0
    )
    total = len(results)
    metrics = {
        "case_count": total,
        "passed_count": sum(1 for item in results if item["passed"]),
        "accepted_match_precision": round(accepted_precision, 3),
        "accepted_match_recall": round(recall, 3),
        "false_match_rate": round(len(false_confident) / total, 3),
        "false_confident_match_rate": round(len(false_confident) / max(len(accepted_actual), 1), 3),
        "false_rejection_rate": round(len(false_rejections) / total, 3),
        "uncertain_rate": round(
            sum(1 for item in results if item["actual_status"] == "uncertain") / total, 3
        ),
        "accessory_rejection_accuracy": _conflict_accuracy(results, "ACCESSORY_MISMATCH"),
        "model_conflict_rejection_accuracy": _conflict_accuracy(results, "MODEL_NUMBER_MISMATCH"),
        "package_mismatch_detection_accuracy": _conflict_accuracy(
            results, "PACKAGE_QUANTITY_MISMATCH"
        ),
        "condition_mismatch_detection_accuracy": _conflict_accuracy(
            results, "CONDITION_MISMATCH"
        ),
        "average_matching_latency_ms": round(statistics.mean(latencies_ms), 3),
        "p95_matching_latency_ms": round(_p95(latencies_ms), 3),
        "dataset_limitation": (
            "Small fixture dataset; precision targets are smoke thresholds, not statistically "
            "meaningful production estimates."
        ),
    }
    report = {"metrics": metrics, "failures": [item for item in results if not item["passed"]]}
    print(json.dumps(report, indent=2))
    if metrics["accepted_match_precision"] < 0.9:
        raise SystemExit("Accepted-match precision is below 90%.")
    if metrics["false_confident_match_rate"] > 0.05:
        raise SystemExit("False confident-match rate is above 5%.")
    if report["failures"]:
        raise SystemExit("Product matcher evaluation failed.")


def _identity(payload: dict[str, Any]) -> ProductIdentity:
    evidence = [
        EvidenceRecord(
            id=f"ev-eval-{normalize_text(payload['product_name']).replace(' ', '-')[:40]}",
            source=EvidenceSource.MODEL_INFERENCE,
            source_reference="product_matcher_eval",
            observation="Fixture canonical product identity",
            confidence=1.0,
        )
    ]
    normalized_title = normalize_text(
        " ".join(part for part in (payload.get("brand"), payload["product_name"]) if part)
    )
    return ProductIdentity(
        brand=payload.get("brand"),
        manufacturer=payload.get("brand"),
        product_name=payload["product_name"],
        product_type=payload.get("product_type"),
        category=payload.get("product_type"),
        model_number=payload.get("model_number"),
        manufacturer_part_number=payload.get("manufacturer_part_number"),
        variant=payload.get("variant"),
        expected_condition=ProductCondition.NEW,
        normalized_title=normalized_title,
        aliases=[payload["product_name"]],
        excluded_terms=[],
        source_evidence=evidence,
    )


def _listing(payload: dict[str, Any]) -> NormalizedMarketplaceListing:
    title = payload["title"]
    pack_quantity, unit_quantity, unit_type = parse_package(title)
    condition = (
        ProductCondition(payload["condition"])
        if payload.get("condition")
        else parse_condition(title) or ProductCondition.NEW
    )
    return NormalizedMarketplaceListing(
        provider="fixture",
        platform="FixtureMarket",
        listing_id=normalize_text(title).replace(" ", "-"),
        title=title,
        normalized_title=normalize_text(title),
        brand=payload.get("brand"),
        model_number=payload.get("model_number") or extract_model_number(title),
        manufacturer_part_number=payload.get("manufacturer_part_number"),
        variant=payload.get("variant"),
        condition=condition,
        pack_quantity=payload.get("pack_quantity", pack_quantity),
        unit_quantity=unit_quantity,
        unit_type=unit_type,
        item_price=decimal_or_none(payload.get("item_price", 100)),
        landed_price=decimal_or_none(payload.get("item_price", 100)),
        currency="USD",
        raw_rank_signals=[RankSignal(name="position", value=1.0, source="fixture")],
        observed_at=datetime.now(UTC),
    )


def _conflict_accuracy(results: list[dict[str, Any]], code: str) -> float:
    relevant = [item for item in results if code in item["expected_conflicts"]]
    if not relevant:
        return 0.0
    matched = sum(1 for item in relevant if code in item["actual_conflicts"])
    return round(matched / len(relevant), 3)


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, math_ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def math_ceil(value: float) -> int:
    rounded = int(value)
    return rounded if rounded == value else rounded + 1


if __name__ == "__main__":
    main()
