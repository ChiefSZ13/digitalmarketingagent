"use client";

import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import type { ProblemDetails } from "@/lib/schemas";

type Props = {
  state: "empty" | "loading" | "success" | "partial-success" | "error";
  error?: Error | null;
  warnings?: string[];
};

function getProblem(error: Error | null | undefined): ProblemDetails | null {
  if (error && "problem" in error) {
    return error.problem as ProblemDetails;
  }
  return null;
}

export function AnalysisProgress({ state, error, warnings = [] }: Props) {
  if (state === "empty") {
    return (
      <section className="rounded border border-gray-200 bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">
          Analysis status
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          No analysis has been run yet.
        </p>
      </section>
    );
  }
  if (state === "loading") {
    return (
      <section
        className="rounded border border-gray-200 bg-white p-5"
        aria-live="polite"
      >
        <div className="flex items-center gap-2">
          <Loader2
            aria-hidden="true"
            className="h-5 w-5 animate-spin text-accent-600"
          />
          <h2 className="text-base font-semibold text-gray-900">
            Analyzing product
          </h2>
        </div>
        <p className="mt-2 text-sm text-gray-600">
          Validating images, running perception, and scoring keywords.
        </p>
      </section>
    );
  }
  if (state === "error") {
    const problem = getProblem(error);
    return (
      <section
        className="rounded border border-red-200 bg-red-50 p-5"
        role="alert"
      >
        <div className="flex items-center gap-2">
          <AlertCircle aria-hidden="true" className="h-5 w-5 text-red-700" />
          <h2 className="text-base font-semibold text-red-900">
            {problem?.title ?? "Analysis failed"}
          </h2>
        </div>
        <p className="mt-2 text-sm text-red-800">
          {problem?.detail ?? error?.message}
        </p>
        {problem?.request_id ? (
          <p className="mt-2 text-xs text-red-700">
            Request ID: {problem.request_id}
          </p>
        ) : null}
      </section>
    );
  }
  return (
    <section className="rounded border border-gray-200 bg-white p-5">
      <div className="flex items-center gap-2">
        <CheckCircle2 aria-hidden="true" className="h-5 w-5 text-green-700" />
        <h2 className="text-base font-semibold text-gray-900">
          {state === "partial-success"
            ? "Analysis complete with warnings"
            : "Analysis complete"}
        </h2>
      </div>
      {warnings.length > 0 ? (
        <ul className="mt-3 space-y-1 text-sm text-amber-800">
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
