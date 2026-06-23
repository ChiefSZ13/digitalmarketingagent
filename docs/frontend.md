# Frontend

The frontend is a single Next.js App Router page in `apps/web/app/page.tsx`.

Component structure:

- `ProductAnalysisForm`: form state, metadata inputs, submit/reset controls
- `ImageDropzone`: drag/drop, file picker, previews, removal, object URL cleanup
- `AnalysisProgress`: empty, loading, success, partial-success, and error states
- `ProductProfilePanel`: product profile sections and claim warnings
- `KeywordClusterSummary`: ranked cluster cards
- `KeywordFilters`: text/category/intent/score filters and sorting
- `KeywordTable`: keyword list with expandable evidence details
- `KeywordDetails`: rationale, score components, evidence references, risk flags
- `JsonExport`: copy/download complete run JSON

API access is isolated in `apps/web/lib/api-client.ts`. The production path calls `NEXT_PUBLIC_API_BASE_URL`. Fixture mode is enabled with `NEXT_PUBLIC_USE_FIXTURES=true` and loads `public/fixtures/mock-run.json`.

The frontend performs display filtering and sorting only. Perception, scoring, classification, clustering, and evidence validation remain backend responsibilities.

