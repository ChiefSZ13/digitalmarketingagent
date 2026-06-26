"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import type { EvidenceRecord, KeywordCandidate } from "@/lib/schemas";
import { percent, titleize } from "@/lib/formatters";
import type { KeywordFilterState } from "./keyword-filters";
import { KeywordDetails } from "./keyword-details";

type Props = {
  keywords: KeywordCandidate[];
  evidence: EvidenceRecord[];
  filters: KeywordFilterState;
};

export function KeywordTable({ keywords, evidence, filters }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const filtered = useMemo(() => {
    const text = filters.text.toLowerCase();
    const searchKeywords = keywords.filter(
      (keyword) => keyword.marketing_term_type === "search_query",
    );
    const result = searchKeywords.filter((keyword) => {
      const matchesText = keyword.text.toLowerCase().includes(text);
      const matchesFamily =
        filters.queryFamily === "all" ||
        keyword.query_family === filters.queryFamily;
      const matchesIntent =
        filters.intent === "all" || keyword.intent === filters.intent;
      const matchesEligibility =
        filters.eligibility === "all" ||
        (filters.eligibility === "eligible" &&
          keyword.eligible_for_live_enrichment) ||
        (filters.eligibility === "not_eligible" &&
          !keyword.eligible_for_live_enrichment);
      return (
        matchesText &&
        matchesFamily &&
        matchesIntent &&
        matchesEligibility &&
        keyword.product_relevance_score >= filters.minRelevance &&
        keyword.query_realism_score >= filters.minRealism
      );
    });
    return [...result].sort((left, right) => {
      if (filters.sort === "text") {
        return left.text.localeCompare(right.text);
      }
      if (filters.sort === "realism") {
        return right.query_realism_score - left.query_realism_score;
      }
      return right.product_relevance_score - left.product_relevance_score;
    });
  }, [filters, keywords]);

  return (
    <section className="min-w-0 rounded border border-gray-200 bg-white p-4 sm:p-5">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-900">
          Keyword candidates
        </h2>
        <span className="text-sm text-gray-600">{filtered.length} shown</span>
      </div>
      <div className="mt-4 min-w-0">
        <table className="w-full border-separate border-spacing-0 text-left text-sm">
          <colgroup className="hidden md:table-column-group">
            <col className="w-[28%]" />
            <col className="w-[14%]" />
            <col className="w-[12%]" />
            <col className="w-[12%]" />
            <col className="w-[12%]" />
            <col className="w-[14%]" />
            <col className="w-[8%]" />
          </colgroup>
          <thead className="hidden md:table-header-group">
            <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
              <th className="py-2 pr-4 font-medium">Keyword</th>
              <th className="py-2 pr-4 font-medium">Query family</th>
              <th className="py-2 pr-4 font-medium">Intent</th>
              <th className="py-2 pr-4 font-medium">Product relevance</th>
              <th className="py-2 pr-4 font-medium">Query realism</th>
              <th className="py-2 pr-4 font-medium">Live metrics</th>
              <th className="py-2 font-medium">Details</th>
            </tr>
          </thead>
          <tbody className="block space-y-3 md:table-row-group md:space-y-0">
            {filtered.map((keyword) => {
              const isExpanded = expanded === keyword.normalized_text;
              return (
                <Fragment key={keyword.normalized_text}>
                  <tr className="block rounded border border-gray-200 p-3 md:table-row md:rounded-none md:border-0 md:p-0">
                    <td className="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-3 py-2 md:table-cell md:py-3 md:pr-4">
                      <span className="text-xs font-medium uppercase text-gray-500 md:hidden">
                        Keyword
                      </span>
                      <span className="min-w-0 break-words font-medium text-gray-900">
                        {keyword.text}
                      </span>
                    </td>
                    <td className="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-3 py-2 md:table-cell md:py-3 md:pr-4">
                      <span className="text-xs font-medium uppercase text-gray-500 md:hidden">
                        Query family
                      </span>
                      <span className="min-w-0 break-words text-gray-700">
                        {titleize(keyword.query_family)}
                      </span>
                    </td>
                    <td className="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-3 py-2 md:table-cell md:py-3 md:pr-4">
                      <span className="text-xs font-medium uppercase text-gray-500 md:hidden">
                        Intent
                      </span>
                      <span className="min-w-0 break-words text-gray-700">
                        {titleize(keyword.intent)}
                      </span>
                    </td>
                    <td className="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-3 py-2 md:table-cell md:py-3 md:pr-4">
                      <span className="text-xs font-medium uppercase text-gray-500 md:hidden">
                        Product relevance
                      </span>
                      <span className="text-gray-700">
                        {percent(keyword.product_relevance_score)}
                      </span>
                    </td>
                    <td className="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-3 py-2 md:table-cell md:py-3 md:pr-4">
                      <span className="text-xs font-medium uppercase text-gray-500 md:hidden">
                        Query realism
                      </span>
                      <span className="text-gray-700">
                        {percent(keyword.query_realism_score)}
                      </span>
                    </td>
                    <td className="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-3 py-2 md:table-cell md:py-3 md:pr-4">
                      <span className="text-xs font-medium uppercase text-gray-500 md:hidden">
                        Live metrics
                      </span>
                      <span className="min-w-0 break-words text-gray-700">
                        {liveMetricsStatus(keyword)}
                      </span>
                    </td>
                    <td className="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-3 py-2 md:table-cell md:py-3">
                      <span className="text-xs font-medium uppercase text-gray-500 md:hidden">
                        Details
                      </span>
                      <span>
                        <button
                          className="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                          type="button"
                          onClick={() =>
                            setExpanded(
                              isExpanded ? null : keyword.normalized_text,
                            )
                          }
                        >
                          {isExpanded ? (
                            <ChevronUp aria-hidden="true" className="h-4 w-4" />
                          ) : (
                            <ChevronDown
                              aria-hidden="true"
                              className="h-4 w-4"
                            />
                          )}
                          Inspect
                        </button>
                      </span>
                    </td>
                  </tr>
                  {isExpanded ? (
                    <tr className="block md:table-row">
                      <td
                        className="block min-w-0 pb-3 md:table-cell md:pr-4"
                        colSpan={7}
                      >
                        <KeywordDetails keyword={keyword} evidence={evidence} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-600">
            No keywords match the current filters.
          </p>
        ) : null}
      </div>
    </section>
  );
}

function liveMetricsStatus(keyword: KeywordCandidate): string {
  const hasLiveMetrics =
    keyword.enrichment.average_monthly_searches !== null ||
    keyword.enrichment.competition_level !== null ||
    keyword.enrichment.cpc_low !== null ||
    keyword.enrichment.cpc_high !== null ||
    keyword.enrichment.trend !== null;
  if (hasLiveMetrics) {
    return "Enriched";
  }
  return keyword.eligible_for_live_enrichment ? "Ready" : "Not eligible";
}
