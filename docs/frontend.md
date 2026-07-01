# Frontend

The frontend is a Next.js App Router app. The main workflow remains
`apps/web/app/page.tsx`, with MVP 2A adding persisted-memory pages.

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

Additional pages:

- `/analyses`: persisted analysis history with search, status/count columns,
  open/copy/export actions, and optional access-key input.
- `/analyses/[id]`: persisted report detail with tabs for overview, product
  profile, marketplace, keywords, provider runs, evidence, and raw JSON.
- `/admin/db`: read-only development database inspector. It displays a warning
  and only works when the backend inspector flag is enabled.

API access is isolated in `apps/web/lib/api-client.ts`. The production path calls `NEXT_PUBLIC_API_BASE_URL`. Fixture mode is enabled with `NEXT_PUBLIC_USE_FIXTURES=true` and loads `public/fixtures/mock-run.json`.

The frontend performs display filtering, sorting, and review actions only.
Perception, marketplace matching, price aggregation, keyword scoring,
classification, clustering, persistence, and evidence validation remain backend
responsibilities. Manual marketplace review actions are persisted separately by
the backend and merged back into reopened reports without mutating raw provider
observations.

The keyword UI renders only `marketing_term_type=search_query` candidates in
the keyword table. Product features, benefits, audience descriptions, and
content ideas remain in the product-profile sections unless the backend emits a
validated short search query for them.
