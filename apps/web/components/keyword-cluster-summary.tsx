"use client";

import type { KeywordCluster } from "@/lib/schemas";
import { percent, titleize } from "@/lib/formatters";

export function KeywordClusterSummary({
  clusters,
}: {
  clusters: KeywordCluster[];
}) {
  if (clusters.length === 0) {
    return (
      <section className="min-w-0 rounded border border-gray-200 bg-white p-4 sm:p-5">
        <h2 className="text-lg font-semibold text-gray-900">
          Keyword clusters
        </h2>
        <p className="mt-2 text-sm text-gray-600">No clusters returned.</p>
      </section>
    );
  }

  return (
    <section className="min-w-0 rounded border border-gray-200 bg-white p-4 sm:p-5">
      <h2 className="text-lg font-semibold text-gray-900">Keyword clusters</h2>
      <div className="mt-4 grid min-w-0 gap-3 sm:grid-cols-2 2xl:grid-cols-3">
        {clusters.map((cluster) => (
          <article
            key={cluster.id}
            className="min-w-0 rounded border border-gray-200 p-4"
          >
            <div className="flex min-w-0 items-start justify-between gap-3">
              <h3 className="min-w-0 break-words text-sm font-semibold text-gray-900">
                {cluster.theme}
              </h3>
              <span className="text-xs font-medium text-gray-600">
                {percent(cluster.aggregate_relevance)}
              </span>
            </div>
            <p className="mt-2 break-words text-sm text-gray-700">
              {cluster.primary_keyword}
            </p>
            <p className="mt-2 text-xs text-gray-500">
              {titleize(cluster.dominant_intent)} intent ·{" "}
              {cluster.member_keywords.length} terms
            </p>
            <p className="mt-3 break-words text-xs text-gray-600">
              {cluster.recommended_usage}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
