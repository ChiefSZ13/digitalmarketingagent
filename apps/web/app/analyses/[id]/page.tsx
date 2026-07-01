"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { JsonExport } from "@/components/json-export";
import { KeywordClusterSummary } from "@/components/keyword-cluster-summary";
import {
  type KeywordFilterState,
  KeywordFilters,
} from "@/components/keyword-filters";
import { KeywordIntelligencePanel } from "@/components/keyword-intelligence-panel";
import { KeywordTable } from "@/components/keyword-table";
import { MarketplaceSnapshotPanel } from "@/components/marketplace-snapshot-panel";
import { ProductProfilePanel } from "@/components/product-profile-panel";
import { ApiProblemError, getAnalysisDetail } from "@/lib/api-client";
import type { AnalysisDetail } from "@/lib/schemas";
import { titleize } from "@/lib/formatters";

const INITIAL_FILTERS: KeywordFilterState = {
  text: "",
  queryFamily: "all",
  intent: "all",
  minRelevance: 0,
  minRealism: 0,
  eligibility: "all",
  sort: "relevance",
};

type Tab =
  | "overview"
  | "profile"
  | "marketplace"
  | "keywords"
  | "providers"
  | "evidence"
  | "json";

export default function AnalysisDetailPage() {
  const params = useParams<{ id: string }>();
  const analysisId = params.id;
  const [accessKey, setAccessKey] = useState("");
  const [detail, setDetail] = useState<AnalysisDetail | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [filters, setFilters] = useState<KeywordFilterState>(INITIAL_FILTERS);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setDetail(await getAnalysisDetail({ analysisId, accessKey }));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setIsLoading(false);
    }
  }, [accessKey, analysisId]);

  useEffect(() => {
    void load();
  }, [load]);

  const report = detail?.report ?? null;
  const queryFamilies = useMemo(
    () =>
      Array.from(
        new Set(
          report?.keyword_candidates
            .filter((keyword) => keyword.marketing_term_type === "search_query")
            .map((keyword) => keyword.query_family) ?? [],
        ),
      ).sort(),
    [report],
  );
  const intents = useMemo(
    () =>
      Array.from(
        new Set(
          report?.keyword_candidates
            .filter((keyword) => keyword.marketing_term_type === "search_query")
            .map((keyword) => keyword.intent) ?? [],
        ),
      ).sort(),
    [report],
  );

  return (
    <main className="min-h-screen bg-white">
      <div className="mx-auto w-full max-w-7xl px-3 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 border-b border-gray-200 pb-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-accent-600">
                Persisted analysis
              </p>
              <h1 className="mt-1 break-words text-2xl font-semibold text-gray-950 sm:text-3xl">
                {detail?.summary.product_name ?? "Analysis report"}
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                {detail ? titleize(detail.summary.status) : analysisId}
              </p>
            </div>
            <Link
              className="rounded border border-gray-300 px-3 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
              href="/analyses"
            >
              History
            </Link>
          </div>
        </header>

        <section className="mb-4 flex flex-wrap items-end gap-3">
          <label className="block min-w-56 text-sm font-medium text-gray-800">
            Access key
            <input
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
              type="password"
              value={accessKey}
              onChange={(event) => setAccessKey(event.target.value)}
              placeholder="Optional"
            />
          </label>
          <button
            className="rounded bg-accent-600 px-4 py-2 text-sm font-medium text-white hover:bg-accent-700 disabled:opacity-60"
            type="button"
            onClick={() => void load()}
            disabled={isLoading}
          >
            Reload
          </button>
        </section>

        {error ? (
          <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {error}
          </p>
        ) : null}

        <nav className="mb-4 flex overflow-x-auto border-b border-gray-200 text-sm">
          {(
            [
              "overview",
              "profile",
              "marketplace",
              "keywords",
              "providers",
              "evidence",
              "json",
            ] as Tab[]
          ).map((item) => (
            <button
              key={item}
              className={`whitespace-nowrap border-b-2 px-4 py-3 font-medium ${
                tab === item
                  ? "border-accent-600 text-accent-700"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
              type="button"
              onClick={() => setTab(item)}
            >
              {titleize(item)}
            </button>
          ))}
        </nav>

        {isLoading && !detail ? (
          <p className="rounded border border-gray-200 p-6 text-center text-sm text-gray-600">
            Loading persisted analysis...
          </p>
        ) : null}

        {detail && report ? (
          <section className="space-y-5">
            {tab === "overview" ? (
              <>
                <Overview detail={detail} />
                <ProductProfilePanel profile={report.product_profile} />
              </>
            ) : null}
            {tab === "profile" ? (
              <ProductProfilePanel profile={report.product_profile} />
            ) : null}
            {tab === "marketplace" ? (
              <MarketplaceSnapshotPanel
                accessKey={accessKey}
                runId={report.run_id}
                snapshot={report.marketplace_snapshot}
              />
            ) : null}
            {tab === "keywords" ? (
              <>
                <KeywordClusterSummary clusters={report.keyword_clusters} />
                <KeywordIntelligencePanel
                  intelligence={report.keyword_intelligence}
                />
                <KeywordFilters
                  value={filters}
                  queryFamilies={queryFamilies}
                  intents={intents}
                  onChange={setFilters}
                />
                <KeywordTable
                  keywords={report.keyword_candidates}
                  evidence={report.product_profile.evidence}
                  filters={filters}
                />
              </>
            ) : null}
            {tab === "providers" ? <ProviderRuns detail={detail} /> : null}
            {tab === "evidence" ? <Evidence detail={detail} /> : null}
            {tab === "json" ? <JsonExport run={report} /> : null}
          </section>
        ) : null}
      </div>
    </main>
  );
}

function Overview({ detail }: { detail: AnalysisDetail }) {
  return (
    <section className="rounded border border-gray-200 bg-white p-4 sm:p-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Status" value={titleize(detail.summary.status)} />
        <Stat
          label="Marketplace observations"
          value={String(detail.summary.marketplace_observation_count)}
        />
        <Stat
          label="Validated matches"
          value={String(detail.summary.validated_match_count)}
        />
        <Stat label="Keywords" value={String(detail.summary.keyword_count)} />
      </div>
    </section>
  );
}

function ProviderRuns({ detail }: { detail: AnalysisDetail }) {
  return (
    <section className="overflow-hidden rounded border border-gray-200 bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-600">
            <tr>
              <th className="px-4 py-3">Provider</th>
              <th className="px-4 py-3">Operation</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Latency</th>
              <th className="px-4 py-3">Results</th>
              <th className="px-4 py-3">Cost</th>
              <th className="px-4 py-3">Started</th>
              <th className="px-4 py-3">Error</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {detail.provider_runs.map((run) => (
              <tr key={run.id}>
                <td className="px-4 py-3 font-medium text-gray-950">
                  {run.provider_name}
                </td>
                <td className="px-4 py-3 text-gray-700">{run.operation}</td>
                <td className="px-4 py-3 text-gray-700">
                  {titleize(run.status)}
                </td>
                <td className="px-4 py-3 text-gray-700">
                  {formatDuration(run.latency_ms)}
                </td>
                <td className="px-4 py-3 text-gray-700">
                  {run.result_count ?? "Unknown"}
                </td>
                <td className="px-4 py-3 text-gray-700">
                  {run.estimated_cost_usd ?? run.actual_cost_usd ?? "Unknown"}
                </td>
                <td className="px-4 py-3 text-gray-700">
                  {formatDate(run.started_at)}
                </td>
                <td className="px-4 py-3 text-gray-700">
                  {run.error_message ?? run.error_type ?? "None"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Evidence({ detail }: { detail: AnalysisDetail }) {
  const evidence = detail.report?.product_profile.evidence ?? [];
  return (
    <section className="rounded border border-gray-200 bg-white p-4 sm:p-5">
      <div className="space-y-3">
        {evidence.map((item) => (
          <article
            key={item.id}
            className="border-b border-gray-100 pb-3 last:border-b-0"
          >
            <h3 className="text-sm font-semibold text-gray-950">{item.id}</h3>
            <p className="mt-1 text-sm text-gray-700">{item.observation}</p>
            <p className="mt-1 text-xs text-gray-500">
              {titleize(item.source)} · confidence{" "}
              {Math.round(item.confidence * 100)}%
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-gray-200 p-4">
      <p className="text-xs font-medium uppercase text-gray-500">{label}</p>
      <p className="mt-2 break-words text-xl font-semibold text-gray-950">
        {value}
      </p>
    </div>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDuration(value: number | null): string {
  if (value === null) {
    return "Unknown";
  }
  return value < 1000 ? `${value} ms` : `${(value / 1000).toFixed(1)} s`;
}

function errorMessage(caught: unknown): string {
  if (caught instanceof ApiProblemError) {
    return caught.problem.detail;
  }
  if (caught instanceof Error) {
    return caught.message;
  }
  return "Persisted analysis could not be loaded.";
}
