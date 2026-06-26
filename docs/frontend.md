# Frontend

The frontend is a single Next.js App Router page in `apps/web/app/page.tsx`.

Component structure:

- `ProductAnalysisForm`: form state, metadata inputs, submit/reset controls
- `ImageDropzone`: drag/drop, file picker, previews, removal, object URL cleanup
- `AnalysisProgress`: empty, loading, success, partial-success, and error states
- `ProductProfilePanel`: product profile sections and claim warnings
- `MarketplaceSnapshotPanel`: validated marketplace rankings, price ranges,
  listing match groups, conflict explanations, and local review controls for
  uncertain listings
- `KeywordClusterSummary`: ranked cluster cards
- `KeywordFilters`: text/query-family/intent/relevance/realism/eligibility filters
  and sorting
- `KeywordTable`: search-query list with live-metrics readiness and expandable
  evidence details
- `KeywordDetails`: rationale, generation scores, source concepts, evidence
  references, risk flags, and rejection reasons
- `JsonExport`: copy/download complete run JSON

API access is isolated in `apps/web/lib/api-client.ts`. The production path calls `NEXT_PUBLIC_API_BASE_URL`. Fixture mode is enabled with `NEXT_PUBLIC_USE_FIXTURES=true` and loads `public/fixtures/mock-run.json`.

The frontend performs display filtering, sorting, and local review overrides
only. Perception, marketplace matching, price aggregation, keyword scoring,
classification, clustering, and evidence validation remain backend
responsibilities. Local marketplace review actions are UI state only in this
milestone and do not mutate raw provider observations.

The keyword UI renders only `marketing_term_type=search_query` candidates in
the keyword table. Product features, benefits, audience descriptions, and
content ideas remain in the product-profile sections unless the backend emits a
validated short search query for them.
