# Keyword Generation Architecture

## Root Cause

The original MVP 1B keyword generator used product-profile prose directly as
keyword material. It concatenated product names, feature sentences, benefit
phrases, use cases, and audience descriptions into one `KeywordCandidate` list.
That produced long descriptive strings such as feature or audience summaries,
which are useful marketing concepts but poor inputs for search-volume, CPC, or
trend providers.

## Current Design

Keyword generation now has a search-query lane:

1. Build a compact search concept set from the normalized product profile.
2. Generate query families from those concepts:
   `brand_product`, `generic_product`, `feature`, `use_case`,
   `problem_solution`, `review`, `comparison`, `transactional`, and
   `local_or_size_specific`.
3. Validate each generated query with deterministic query-realism rules.
4. Return only eligible `search_query` candidates in `keyword_candidates`.
5. Keep product features, benefits, audience descriptions, and content ideas in
   their own product-profile sections instead of sending them to live keyword
   enrichment.

The `KeywordCandidate` response keeps backward-compatible fields such as
`text`, `normalized_text`, `category`, `intent`, `relevance_score`, and
`confidence_score`, and adds explicit search-query fields:

- `marketing_term_type`
- `query_family`
- `generation_confidence`
- `product_relevance_score`
- `query_realism_score`
- `specificity_score`
- `commercial_intent_score`
- `source_concepts`
- `rejection_reasons`
- `eligible_for_live_enrichment`
- `generator_version`

`confidence_score` and `generation_confidence` mean confidence in generating a
relevant realistic query. They are not search volume, rank, competition, CPC, or
trend estimates.

## Validation Policy

The search-query validator accepts short human-style queries and rejects:

- fewer than 2 words;
- more than 10 words;
- sentence punctuation;
- phrases such as `features a`, `comes with`, `allows the`, `it uses`,
  `includes an`, `designed to provide`, `which makes it`, and `this product`;
- long product-description copies detected by n-gram overlap;
- excessively dense attribute strings;
- low product relevance;
- low query realism.

Normal long-tail queries should stay under 8 words. The absolute hard limit is
10 words.

## Evaluation

Run:

```bash
make evaluate-keyword-generation
```

The smoke evaluation covers air conditioner, Xbox controller, coffee maker, and
running shoes examples. It reports generated query count, average and maximum
word count, over-8/over-10-word rates, duplicate rate, expected-query recall,
bad-query rejection rate, description-copy rejection count, and query-family
coverage.
