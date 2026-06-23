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

