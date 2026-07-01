"use client";

import { Copy, Download, ExternalLink, RefreshCw, Search } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ApiProblemError,
  getAnalysisReport,
  listAnalyses,
} from "@/lib/api-client";
import type { AnalysisListResponse, AnalysisSummary } from "@/lib/schemas";
import { titleize } from "@/lib/formatters";

export default function AnalysesPage() {
  const [accessKey, setAccessKey] = useState("");
  const [search, setSearch] = useState("");
  const [data, setData] = useState<AnalysisListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setData(
        await listAnalyses({
          accessKey,
          search,
          limit: 50,
        }),
      );
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setIsLoading(false);
    }
  }, [accessKey, search]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="min-h-screen bg-white">
      <div className="mx-auto w-full max-w-7xl px-3 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 border-b border-gray-200 pb-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-accent-600">MVP 2A</p>
              <h1 className="mt-1 text-2xl font-semibold text-gray-950 sm:text-3xl">
                Analysis history
              </h1>
            </div>
            <Link
              className="rounded border border-gray-300 px-3 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
              href="/"
            >
              New analysis
            </Link>
          </div>
        </header>

        <section className="mb-4 grid gap-3 md:grid-cols-[minmax(180px,260px)_minmax(220px,1fr)_auto]">
          <label className="block text-sm font-medium text-gray-800">
            Access key
            <input
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
              type="password"
              value={accessKey}
              onChange={(event) => setAccessKey(event.target.value)}
              placeholder="Optional"
            />
          </label>
          <label className="block text-sm font-medium text-gray-800">
            Search
            <span className="relative mt-1 block">
              <Search
                aria-hidden="true"
                className="absolute left-3 top-2.5 h-4 w-4 text-gray-400"
              />
              <input
                className="w-full rounded border border-gray-300 py-2 pl-9 pr-3 text-sm"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Product, brand, or description"
              />
            </span>
          </label>
          <button
            className="inline-flex items-center justify-center gap-2 self-end rounded bg-accent-600 px-4 py-2 text-sm font-medium text-white hover:bg-accent-700 disabled:opacity-60"
            type="button"
            onClick={() => void load()}
            disabled={isLoading}
          >
            <RefreshCw aria-hidden="true" className="h-4 w-4" />
            Refresh
          </button>
        </section>

        {error ? (
          <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {error}
          </p>
        ) : null}

        <section className="overflow-hidden rounded border border-gray-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-600">
                <tr>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">Brand</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Marketplace</th>
                  <th className="px-4 py-3">Keywords</th>
                  <th className="px-4 py-3">Providers</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {(data?.items ?? []).map((analysis) => (
                  <AnalysisRow
                    key={analysis.analysis_id}
                    accessKey={accessKey}
                    analysis={analysis}
                  />
                ))}
                {!isLoading && data?.items.length === 0 ? (
                  <tr>
                    <td
                      className="px-4 py-8 text-center text-gray-600"
                      colSpan={9}
                    >
                      No persisted analyses found.
                    </td>
                  </tr>
                ) : null}
                {isLoading ? (
                  <tr>
                    <td
                      className="px-4 py-8 text-center text-gray-600"
                      colSpan={9}
                    >
                      Loading analyses...
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}

function AnalysisRow({
  analysis,
  accessKey,
}: {
  analysis: AnalysisSummary;
  accessKey: string;
}) {
  async function exportJson() {
    const report = await getAnalysisReport({
      analysisId: analysis.analysis_id,
      accessKey,
    });
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${analysis.run_id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <tr className="align-top">
      <td className="whitespace-nowrap px-4 py-3 text-gray-700">
        {formatDate(analysis.created_at)}
      </td>
      <td className="min-w-52 px-4 py-3 font-medium text-gray-950">
        {analysis.product_name ?? "Unknown product"}
      </td>
      <td className="px-4 py-3 text-gray-700">{analysis.brand ?? "Unknown"}</td>
      <td className="px-4 py-3">
        <span className="rounded bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800">
          {titleize(analysis.status)}
        </span>
      </td>
      <td className="px-4 py-3 text-gray-700">
        {analysis.marketplace_observation_count} observations,{" "}
        {analysis.validated_match_count} matches
      </td>
      <td className="px-4 py-3 text-gray-700">{analysis.keyword_count}</td>
      <td className="px-4 py-3 text-gray-700">
        {titleize(analysis.provider_status)}
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-gray-700">
        {formatDuration(analysis.duration_ms)}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-2">
          <Link
            className="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-800 hover:bg-gray-50"
            href={`/analyses/${analysis.analysis_id}`}
          >
            <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
            Open
          </Link>
          <button
            className="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-800 hover:bg-gray-50"
            type="button"
            onClick={() => navigator.clipboard.writeText(analysis.analysis_id)}
          >
            <Copy aria-hidden="true" className="h-3.5 w-3.5" />
            ID
          </button>
          <button
            className="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-800 hover:bg-gray-50"
            type="button"
            onClick={() => void exportJson()}
          >
            <Download aria-hidden="true" className="h-3.5 w-3.5" />
            JSON
          </button>
        </div>
      </td>
    </tr>
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
  if (value < 1000) {
    return `${value} ms`;
  }
  return `${(value / 1000).toFixed(1)} s`;
}

function errorMessage(caught: unknown): string {
  if (caught instanceof ApiProblemError) {
    return caught.problem.detail;
  }
  if (caught instanceof Error) {
    return caught.message;
  }
  return "Analysis history could not be loaded.";
}
