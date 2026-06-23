from pathlib import Path
import json


REQUIRED_SCENARIOS = {
    "simple_single_object",
    "packaging_text",
    "visually_ambiguous",
    "conflicting_image_description",
    "risky_health_claim",
    "model_number",
    "distracting_background",
    "non_product_image",
    "low_resolution_image",
    "multilingual_description",
}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    fixture_dir = root / "tests" / "evals" / "fixtures"
    manifests = [json.loads(path.read_text(encoding="utf-8")) for path in fixture_dir.glob("*.json")]
    names = {manifest["scenario"] for manifest in manifests}
    missing = REQUIRED_SCENARIOS.difference(names)
    if missing:
        raise SystemExit(f"Missing eval scenarios: {sorted(missing)}")
    print(
        json.dumps(
            {
                "scenario_count": len(manifests),
                "required_scenarios_present": True,
                "metrics_recorded": [
                    "schema_valid_response_rate",
                    "attribute_precision",
                    "unsupported_claim_rate",
                    "evidence_coverage",
                    "keyword_relevance",
                    "duplicate_rate",
                    "category_accuracy",
                    "latency",
                    "cost_per_run",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

