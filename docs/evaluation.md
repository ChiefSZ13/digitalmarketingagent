# Evaluation

Evaluation fixtures live in `tests/evals/fixtures`.

The required scenarios are:

- simple single-object product
- product with packaging text
- visually ambiguous product
- conflicting image and description
- product with risky health claim
- product with model number
- product photographed with distracting background
- non-product image
- low-resolution image
- multilingual description

Run:

```bash
make test-evals
```

The MVP runner verifies fixture coverage and records the metrics that future prompt/model changes must track: schema-valid response rate, attribute precision, unsupported-claim rate, evidence coverage, keyword relevance, duplicate rate, category accuracy, latency, and cost per run.

Keyword-generation realism has a separate smoke runner:

```bash
make evaluate-keyword-generation
```

It verifies short human-style query generation for air conditioner, Xbox
controller, coffee maker, and running shoes fixtures. It reports average and
maximum query length, over-8/over-10-word rates, duplicate rate, expected-query
recall, bad-query rejection rate, description-copy rejections, and query-family
coverage.

## Product Matcher Evaluation

Product-validation fixtures live in `tests/evals/product_matcher_cases.json`.
They cover exact model matches, brand aliases, title word-order differences,
model and part-number conflicts, accessories, package differences, bundles,
condition differences, variant differences, and ambiguous generic products.

Run:

```bash
make evaluate-product-matcher
```

The command reports accepted-match precision, recall, false-match rate, false
confident-match rate, false-rejection rate, uncertain rate, conflict-specific
accuracies, average matching latency, and p95 matching latency.

Current fixture baseline:

- 19 cases.
- Accepted-match precision: 1.0.
- False confident-match rate: 0.0.
- p95 matching latency: about 0.12 ms on the local test run.

The fixture set is intentionally small, so these are smoke thresholds rather
than statistically meaningful production estimates.
