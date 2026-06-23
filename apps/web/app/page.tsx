"use client";

import {
  QueryClient,
  QueryClientProvider,
  useMutation,
} from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { AnalysisProgress } from "@/components/analysis-progress";
import { JsonExport } from "@/components/json-export";
import { KeywordClusterSummary } from "@/components/keyword-cluster-summary";
import {
  type KeywordFilterState,
  KeywordFilters,
} from "@/components/keyword-filters";
import { KeywordTable } from "@/components/keyword-table";
import { ProductAnalysisForm } from "@/components/product-analysis-form";
import { ProductProfilePanel } from "@/components/product-profile-panel";
import { ApiProblemError, createPerceptionRun } from "@/lib/api-client";
import type { AnalysisFormValues, PerceptionRun } from "@/lib/schemas";

const INITIAL_FILTERS: KeywordFilterState = {
  text: "",
  category: "all",
  intent: "all",
  minRelevance: 0,
  minConfidence: 0,
  sort: "relevance",
};

export default function Page() {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <ProductPerceptionPage />
    </QueryClientProvider>
  );
}

function ProductPerceptionPage() {
  const [run, setRun] = useState<PerceptionRun | null>(null);
  const [filters, setFilters] = useState<KeywordFilterState>(INITIAL_FILTERS);
  const mutation = useMutation({
    mutationFn: ({
      values,
      files,
    }: {
      values: AnalysisFormValues;
      files: File[];
    }) => createPerceptionRun(values, files),
    onSuccess: (result) => {
      setRun(result);
      setFilters(INITIAL_FILTERS);
    },
  });

  const categories = useMemo(
    () =>
      Array.from(
        new Set(
          run?.keyword_candidates.map((keyword) => keyword.category) ?? [],
        ),
      ).sort(),
    [run],
  );
  const intents = useMemo(
    () =>
      Array.from(
        new Set(run?.keyword_candidates.map((keyword) => keyword.intent) ?? []),
      ).sort(),
    [run],
  );
  const status: "empty" | "loading" | "success" | "partial-success" | "error" =
    mutation.isPending
      ? "loading"
      : mutation.isError
        ? "error"
        : run
          ? run.warnings.length > 0 || run.errors.length > 0
            ? "partial-success"
            : "success"
          : "empty";

  const error =
    mutation.error instanceof ApiProblemError ? mutation.error : mutation.error;

  return (
    <main className="min-h-screen overflow-x-clip bg-white">
      <div className="mx-auto w-full max-w-7xl px-3 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 border-b border-gray-200 pb-5">
          <p className="text-sm font-medium text-accent-600">MVP 1B</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-normal text-gray-950 sm:text-3xl">
            Product Perception and Keyword Intelligence
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-gray-600">
            Upload product images and a description to generate an
            evidence-backed profile and categorized keyword clusters.
          </p>
        </header>

        <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(320px,420px)_minmax(0,1fr)]">
          <aside className="min-w-0 space-y-5">
            <ProductAnalysisForm
              isSubmitting={mutation.isPending}
              onSubmit={(values, files) => mutation.mutate({ values, files })}
              onReset={() => {
                setRun(null);
                setFilters(INITIAL_FILTERS);
                mutation.reset();
              }}
            />
            <AnalysisProgress
              state={status}
              error={error}
              warnings={run?.warnings}
            />
          </aside>
          <section className="min-w-0 space-y-5">
            {run ? (
              <>
                <ProductProfilePanel profile={run.product_profile} />
                <KeywordClusterSummary clusters={run.keyword_clusters} />
                <KeywordFilters
                  value={filters}
                  categories={categories}
                  intents={intents}
                  onChange={setFilters}
                />
                <KeywordTable
                  keywords={run.keyword_candidates}
                  evidence={run.product_profile.evidence}
                  filters={filters}
                />
                <JsonExport run={run} />
              </>
            ) : (
              <section className="min-w-0 rounded border border-gray-200 bg-white p-8 text-center">
                <h2 className="text-lg font-semibold text-gray-900">
                  Results will appear here
                </h2>
                <p className="mt-2 text-sm text-gray-600">
                  The product profile, keyword clusters, evidence, and JSON
                  export are shown after a run.
                </p>
              </section>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
