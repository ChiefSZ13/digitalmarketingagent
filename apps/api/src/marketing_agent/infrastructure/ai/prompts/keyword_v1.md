# Keyword Prompt v1

Generate only realistic human search queries from the normalized product
profile. Do not turn product features, benefits, audience descriptions, or
content ideas into keyword candidates unless they are rewritten as short search
queries.

Rules:

- Output search-query candidates only.
- Preferred length is 2 to 6 words.
- Absolute maximum is 10 words.
- Do not output full sentences, marketing copy, or explanatory phrases.
- Do not copy long spans from the product description.
- Do not claim search volume, CPC, rank, competition, or trend data.
- Keep content topics, product features, product benefits, and audience
  descriptions separate from search-query candidates.

Good examples:

- `window air conditioner`
- `u shaped window ac`
- `xbox controller review`
- `programmable coffee maker`
- `running shoes price`

Bad examples:

- `this product features a u shaped design that allows the window to open`
- `coffee maker comes with a thermal carafe and programmable timer`
- `lightweight cushioned running shoes designed to provide daily comfort`
- `for people who want better console gaming`

Return structured candidates with evidence IDs, query family, intent, product
relevance, query realism, generation confidence, source concepts, rejection
reasons, and live-enrichment eligibility. Search volume, CPC, competition, and
trend fields must remain empty unless a live keyword-data provider supplies
them.
