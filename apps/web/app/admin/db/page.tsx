"use client";

import { Database, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ApiProblemError,
  listAdminDbRows,
  listAdminDbTables,
} from "@/lib/api-client";
import type {
  AdminDbTableRowsResponse,
  AdminDbTableSummary,
} from "@/lib/schemas";

export default function AdminDbPage() {
  const [accessKey, setAccessKey] = useState("");
  const [tables, setTables] = useState<AdminDbTableSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [rows, setRows] = useState<AdminDbTableRowsResponse | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadTables = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await listAdminDbTables(accessKey);
      setTables(response.tables);
      setSelected((current) => current ?? response.tables[0]?.name ?? null);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setIsLoading(false);
    }
  }, [accessKey]);

  const loadRows = useCallback(async () => {
    if (!selected) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      setRows(
        await listAdminDbRows({
          tableName: selected,
          accessKey,
          search,
        }),
      );
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setIsLoading(false);
    }
  }, [accessKey, search, selected]);

  useEffect(() => {
    void loadTables();
  }, [loadTables]);

  useEffect(() => {
    void loadRows();
  }, [loadRows]);

  return (
    <main className="min-h-screen bg-white">
      <div className="mx-auto w-full max-w-7xl px-3 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 border-b border-gray-200 pb-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-accent-600">
                Developer tool
              </p>
              <h1 className="mt-1 text-2xl font-semibold text-gray-950 sm:text-3xl">
                Database inspector
              </h1>
            </div>
            <Link
              className="rounded border border-gray-300 px-3 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
              href="/analyses"
            >
              Analysis history
            </Link>
          </div>
        </header>

        <p className="mb-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Development database inspector. Do not enable publicly without
          authentication.
        </p>

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
            Search selected table
            <input
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Basic text search"
            />
          </label>
          <button
            className="inline-flex items-center justify-center gap-2 self-end rounded bg-accent-600 px-4 py-2 text-sm font-medium text-white hover:bg-accent-700 disabled:opacity-60"
            type="button"
            onClick={() => {
              void loadTables();
              void loadRows();
            }}
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

        <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="rounded border border-gray-200 bg-white">
            <div className="border-b border-gray-200 p-3 text-sm font-semibold text-gray-900">
              Tables
            </div>
            <div className="max-h-[70vh] overflow-y-auto">
              {tables.map((table) => (
                <button
                  key={table.name}
                  className={`flex w-full items-center justify-between gap-2 border-b border-gray-100 px-3 py-2 text-left text-sm hover:bg-gray-50 ${
                    selected === table.name
                      ? "bg-accent-50 text-accent-700"
                      : "text-gray-800"
                  }`}
                  type="button"
                  onClick={() => setSelected(table.name)}
                >
                  <span className="inline-flex min-w-0 items-center gap-2">
                    <Database aria-hidden="true" className="h-4 w-4 shrink-0" />
                    <span className="truncate">{table.name}</span>
                  </span>
                  <span className="text-xs text-gray-500">
                    {table.record_count ?? "?"}
                  </span>
                </button>
              ))}
            </div>
          </aside>

          <section className="min-w-0 overflow-hidden rounded border border-gray-200 bg-white">
            <div className="border-b border-gray-200 p-3">
              <h2 className="text-sm font-semibold text-gray-900">
                {rows?.table_name ?? selected ?? "No table selected"}
              </h2>
            </div>
            <pre className="max-h-[70vh] overflow-auto p-4 text-xs text-gray-900">
              {rows ? JSON.stringify(rows.rows, null, 2) : "No records loaded."}
            </pre>
          </section>
        </div>
      </div>
    </main>
  );
}

function errorMessage(caught: unknown): string {
  if (caught instanceof ApiProblemError) {
    return caught.problem.detail;
  }
  if (caught instanceof Error) {
    return caught.message;
  }
  return "Database inspector could not be loaded.";
}
