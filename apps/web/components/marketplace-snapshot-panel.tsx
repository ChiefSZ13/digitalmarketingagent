"use client";

import { AlertTriangle } from "lucide-react";
import type { MarketplaceSnapshot } from "@/lib/schemas";
import { compactNumber, moneyRange, percent, titleize } from "@/lib/formatters";

export function MarketplaceSnapshotPanel({
  snapshot,
}: {
  snapshot: MarketplaceSnapshot;
}) {
  return (
    <section className="min-w-0 rounded border border-gray-200 bg-white p-4 sm:p-5">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-gray-900">
            Marketplace Snapshot
          </h2>
          <p className="mt-1 break-words text-sm text-gray-600">
            {snapshot.summary}
          </p>
          <p className="mt-2 break-words text-xs text-gray-500">
            {snapshot.source_provider} · {snapshot.source_query} ·{" "}
            {new Date(snapshot.retrieved_at).toLocaleString()}
          </p>
        </div>
        <span className="rounded border border-gray-200 px-2 py-1 text-xs font-medium text-gray-700">
          Confidence {percent(snapshot.overall_confidence)}
        </span>
      </div>

      {!snapshot.is_live_data ? (
        <div className="mt-4 flex gap-2 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <AlertTriangle
            aria-hidden="true"
            className="mt-0.5 h-4 w-4 flex-none"
          />
          <p>
            Mock or non-live data. Enable a marketplace data provider for live
            offer and price observations.
          </p>
        </div>
      ) : null}

      <div className="mt-5 grid min-w-0 gap-5 2xl:grid-cols-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-900">
            Platform ranking
          </h3>
          <div className="mt-3 space-y-3">
            {snapshot.platform_rankings.map((platform) => (
              <article
                key={`${platform.rank}-${platform.platform}`}
                className="min-w-0 rounded border border-gray-200 p-3"
              >
                <div className="flex min-w-0 items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="break-words text-sm font-semibold text-gray-900">
                      {platform.rank}. {platform.platform}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      {titleize(platform.platform_type)} · potential{" "}
                      {percent(platform.estimated_sales_potential_score)}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      {platform.observed_offer_count ?? 0} offers ·{" "}
                      {compactNumber(platform.observed_review_count)} reviews
                      {platform.observed_units_sold !== null
                        ? ` · ${compactNumber(platform.observed_units_sold)} sold`
                        : ""}
                    </p>
                  </div>
                  <span className="text-xs font-medium text-gray-600">
                    {percent(platform.confidence)}
                  </span>
                </div>
                <p className="mt-2 break-words text-xs text-gray-600">
                  {platform.sales_rank_basis}
                </p>
                <p className="mt-2 break-words text-xs text-gray-500">
                  {platform.listing_search_phrase}
                </p>
                {platform.source_url ? (
                  <a
                    className="mt-2 inline-block break-all text-xs font-medium text-accent-700 hover:text-accent-800"
                    href={platform.source_url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Source result
                  </a>
                ) : null}
              </article>
            ))}
          </div>
        </div>

        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-900">Price ranges</h3>
          <div className="mt-3 overflow-hidden rounded border border-gray-200">
            <table className="w-full table-fixed text-left text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="w-[35%] px-3 py-2 font-medium">Platform</th>
                  <th className="w-[30%] px-3 py-2 font-medium">Range</th>
                  <th className="w-[35%] px-3 py-2 font-medium">Basis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {snapshot.price_estimates.map((price) => (
                  <tr key={price.platform}>
                    <td className="px-3 py-3 font-medium text-gray-900">
                      <span className="break-words">{price.platform}</span>
                    </td>
                    <td className="px-3 py-3 text-gray-700">
                      {moneyRange(
                        price.price_low,
                        price.price_high,
                        price.currency,
                      )}
                    </td>
                    <td className="px-3 py-3 text-xs text-gray-600">
                      <span className="break-words">
                        {price.observed_offer_count ?? 0} offers ·{" "}
                        {price.price_basis}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="mt-5 grid min-w-0 gap-3 lg:grid-cols-2">
        <div className="min-w-0 rounded border border-gray-200 p-3">
          <h3 className="text-sm font-semibold text-gray-900">Methodology</h3>
          <p className="mt-2 break-words text-sm text-gray-600">
            {snapshot.methodology}
          </p>
        </div>
        <div className="min-w-0 rounded border border-gray-200 p-3">
          <h3 className="text-sm font-semibold text-gray-900">Limitations</h3>
          <ul className="mt-2 space-y-1 text-sm text-gray-600">
            {snapshot.limitations.map((limitation) => (
              <li key={limitation} className="break-words">
                {limitation}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
