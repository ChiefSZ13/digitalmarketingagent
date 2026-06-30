"use client";

import { Search, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import type {
  KeywordIntelligence,
  KeywordIntelligenceKeyword,
} from "@/lib/schemas";
import { moneyRange, percent, titleize } from "@/lib/formatters";

type Props = {
  intelligence: KeywordIntelligence;
};

type Filters = {
  text: string;
  intent: string;
  origin: string;
  competition: string;
  trend: string;
  liveMetrics: "all" | "with_metrics" | "missing_metrics";
};

const INITIAL_FILTERS: Filters = {
  text: "",
  intent: "all",
  origin: "all",
  competition: "all",
  trend: "all",
  liveMetrics: "all",
};

export function KeywordIntelligencePanel({ intelligence }: Props) {
  const [filters, setFilters] = useState<Filters>(INITIAL_FILTERS);
  const options = useMemo(
    () => buildOptions(intelligence.keywords),
    [intelligence.keywords],
  );
  const filtered = useMemo(
    () => filterKeywords(intelligence.keywords, filters),
    [filters, intelligence.keywords],
  );
  const enrichedCount = intelligence.keywords.filter(
    (keyword) => keyword.metrics,
  ).length;
  const relatedCount = intelligence.keywords.filter((keyword) =>
    keyword.origins.includes("provider_related_term"),
  ).length;
  const opportunityValues = intelligence.keywords
    .map((keyword) => keyword.opportunity_score)
    .filter((value): value is number => value !== null);
  const averageOpportunity =
    opportunityValues.length > 0
      ? opportunityValues.reduce((sum, value) => sum + value, 0) /
        opportunityValues.length
      : null;

  return (
    <section className="min-w-0 rounded border border-gray-200 bg-white p-4 sm:p-5">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-gray-900">
            Keyword Intelligence
          </h2>
          <p className="mt-1 break-words text-sm text-gray-600">
            {titleize(intelligence.status)} · {intelligence.provider} ·{" "}
            {intelligence.market}/{intelligence.language} ·{" "}
            {new Date(intelligence.collected_at).toLocaleString()}
          </p>
        </div>
        <span className="rounded border border-gray-200 px-2 py-1 text-xs font-medium text-gray-700">
          {enrichedCount} enriched
        </span>
      </div>

      <div className="mt-4 grid min-w-0 gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Keywords" value={String(intelligence.keywords.length)} />
        <Metric label="Live metrics" value={`${enrichedCount}`} />
        <Metric label="Related terms" value={`${relatedCount}`} />
        <Metric
          label="Avg opportunity"
          value={
            averageOpportunity === null
              ? "Insufficient"
              : percent(averageOpportunity)
          }
        />
      </div>

      {intelligence.warnings.length > 0 ? (
        <div className="mt-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          {intelligence.warnings.map((warning) => (
            <p key={warning} className="break-words">
              {warning}
            </p>
          ))}
        </div>
      ) : null}

      <div className="mt-4 grid min-w-0 gap-3 lg:grid-cols-[minmax(220px,1.4fr)_repeat(5,minmax(120px,1fr))]">
        <label className="min-w-0">
          <span className="block text-sm font-medium text-gray-900">
            Search
          </span>
          <span className="mt-2 flex min-w-0 items-center rounded border border-gray-300 px-3">
            <Search aria-hidden="true" className="h-4 w-4 text-gray-500" />
            <input
              className="min-w-0 flex-1 border-0 px-2 py-2 text-sm outline-none"
              type="search"
              value={filters.text}
              onChange={(event) =>
                setFilters({ ...filters, text: event.target.value })
              }
            />
          </span>
        </label>
        <Select
          label="Intent"
          options={options.intents}
          value={filters.intent}
          onChange={(intent) => setFilters({ ...filters, intent })}
        />
        <Select
          label="Origin"
          options={options.origins}
          value={filters.origin}
          onChange={(origin) => setFilters({ ...filters, origin })}
        />
        <Select
          label="Competition"
          options={options.competitions}
          value={filters.competition}
          onChange={(competition) => setFilters({ ...filters, competition })}
        />
        <Select
          label="Trend"
          options={options.trends}
          value={filters.trend}
          onChange={(trend) => setFilters({ ...filters, trend })}
        />
        <Select
          label="Metrics"
          options={["with_metrics", "missing_metrics"]}
          value={filters.liveMetrics}
          onChange={(liveMetrics) =>
            setFilters({
              ...filters,
              liveMetrics: liveMetrics as Filters["liveMetrics"],
            })
          }
        />
      </div>

      <div className="mt-4 min-w-0 overflow-x-auto">
        <table className="w-full min-w-[900px] table-fixed text-left text-sm">
          <thead className="border-b border-gray-200 text-xs uppercase text-gray-500">
            <tr>
              <th className="w-[18%] py-2 pr-3 font-medium">Keyword</th>
              <th className="w-[10%] py-2 pr-3 font-medium">Origin</th>
              <th className="w-[10%] py-2 pr-3 font-medium">Intent</th>
              <th className="w-[10%] py-2 pr-3 font-medium">Relevance</th>
              <th className="w-[10%] py-2 pr-3 font-medium">Volume</th>
              <th className="w-[12%] py-2 pr-3 font-medium">CPC</th>
              <th className="w-[10%] py-2 pr-3 font-medium">Competition</th>
              <th className="w-[10%] py-2 pr-3 font-medium">Trend</th>
              <th className="w-[10%] py-2 font-medium">Opportunity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map((keyword) => (
              <tr key={keyword.normalized_text}>
                <td className="py-3 pr-3 align-top">
                  <details className="min-w-0">
                    <summary className="cursor-pointer break-words font-medium text-gray-900">
                      {keyword.text}
                    </summary>
                    <KeywordMetricDetails keyword={keyword} />
                  </details>
                </td>
                <td className="py-3 pr-3 align-top text-gray-700">
                  {keyword.origins.map(titleize).join(", ")}
                </td>
                <td className="py-3 pr-3 align-top text-gray-700">
                  {titleize(keyword.intent)}
                </td>
                <td className="py-3 pr-3 align-top text-gray-700">
                  {percent(keyword.product_relevance_score)}
                </td>
                <td className="py-3 pr-3 align-top text-gray-700">
                  {numberOrMissing(keyword.metrics?.average_monthly_searches)}
                </td>
                <td className="py-3 pr-3 align-top text-gray-700">
                  {cpcLabel(keyword)}
                </td>
                <td className="py-3 pr-3 align-top text-gray-700">
                  {keyword.metrics?.competition
                    ? titleize(keyword.metrics.competition)
                    : "Missing"}
                </td>
                <td className="py-3 pr-3 align-top text-gray-700">
                  {keyword.metrics
                    ? titleize(keyword.metrics.trend_direction)
                    : "Missing"}
                </td>
                <td className="py-3 align-top text-gray-700">
                  {keyword.opportunity_score === null
                    ? "Insufficient"
                    : percent(keyword.opportunity_score)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-600">
            No keyword intelligence rows match the current filters.
          </p>
        ) : null}
      </div>

      <div className="mt-4 flex min-w-0 gap-2 rounded border border-gray-200 p-3 text-sm text-gray-600">
        <SlidersHorizontal
          aria-hidden="true"
          className="mt-0.5 h-4 w-4 flex-none"
        />
        <p className="break-words">
          {intelligence.methodology.notes.join(" ")}
        </p>
      </div>
    </section>
  );
}

function KeywordMetricDetails({
  keyword,
}: {
  keyword: KeywordIntelligenceKeyword;
}) {
  const metrics = keyword.metrics;
  return (
    <div className="mt-3 min-w-0 space-y-2 rounded border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
      <p className="break-words">{keyword.rationale}</p>
      {keyword.related_to ? (
        <p className="break-words">Related to: {keyword.related_to}</p>
      ) : null}
      {metrics ? (
        <>
          <p className="break-words">
            Provider: {metrics.provider} · matched{" "}
            {metrics.matched_provider_term} (
            {titleize(metrics.provider_match_type)},{" "}
            {percent(metrics.provider_match_confidence)})
          </p>
          <p className="break-words">
            Freshness: {new Date(metrics.retrieved_at).toLocaleString()} ·{" "}
            {metrics.market}/{metrics.language}
          </p>
          <p className="break-words">
            Trend: {titleize(metrics.trend_direction)}
            {metrics.trend_explanation ? ` · ${metrics.trend_explanation}` : ""}
          </p>
          {keyword.opportunity_components ? (
            <p className="break-words">
              Score components: demand{" "}
              {scoreOrMissing(keyword.opportunity_components.market_demand)},
              competition{" "}
              {scoreOrMissing(
                keyword.opportunity_components.competition_advantage,
              )}
              , CPC{" "}
              {scoreOrMissing(keyword.opportunity_components.cpc_efficiency)},
              trend{" "}
              {scoreOrMissing(keyword.opportunity_components.trend_signal)},
              completeness{" "}
              {percent(keyword.opportunity_components.data_completeness)}
            </p>
          ) : null}
          {metrics.monthly_history.length > 0 ? (
            <p className="break-words">
              Monthly history:{" "}
              {metrics.monthly_history
                .map(
                  (point) =>
                    `${point.year}-${String(point.month).padStart(2, "0")}: ${point.searches}`,
                )
                .join(", ")}
            </p>
          ) : (
            <p>Monthly history: Missing</p>
          )}
        </>
      ) : (
        <p>No provider metrics were available for this keyword.</p>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded border border-gray-200 px-3 py-2">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 break-words text-lg font-semibold text-gray-900">
        {value}
      </p>
    </div>
  );
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="min-w-0">
      <span className="block text-sm font-medium text-gray-900">{label}</span>
      <select
        className="mt-2 min-w-0 w-full rounded border border-gray-300 px-3 py-2 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="all">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {titleize(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function filterKeywords(
  keywords: KeywordIntelligenceKeyword[],
  filters: Filters,
): KeywordIntelligenceKeyword[] {
  const text = filters.text.toLowerCase();
  return keywords
    .filter((keyword) => {
      const matchesText = keyword.text.toLowerCase().includes(text);
      const matchesIntent =
        filters.intent === "all" || keyword.intent === filters.intent;
      const matchesOrigin =
        filters.origin === "all" || keyword.origins.includes(filters.origin);
      const competition = keyword.metrics?.competition ?? "missing";
      const trend = keyword.metrics?.trend_direction ?? "missing";
      const matchesCompetition =
        filters.competition === "all" || competition === filters.competition;
      const matchesTrend = filters.trend === "all" || trend === filters.trend;
      const matchesMetrics =
        filters.liveMetrics === "all" ||
        (filters.liveMetrics === "with_metrics" && keyword.metrics !== null) ||
        (filters.liveMetrics === "missing_metrics" && keyword.metrics === null);
      return (
        matchesText &&
        matchesIntent &&
        matchesOrigin &&
        matchesCompetition &&
        matchesTrend &&
        matchesMetrics
      );
    })
    .sort((left, right) => {
      const leftScore = left.opportunity_score ?? left.product_relevance_score;
      const rightScore =
        right.opportunity_score ?? right.product_relevance_score;
      return rightScore - leftScore;
    });
}

function buildOptions(keywords: KeywordIntelligenceKeyword[]) {
  return {
    intents: Array.from(
      new Set(keywords.map((keyword) => keyword.intent)),
    ).sort(),
    origins: Array.from(
      new Set(keywords.flatMap((keyword) => keyword.origins)),
    ).sort(),
    competitions: Array.from(
      new Set(
        keywords.map((keyword) => keyword.metrics?.competition ?? "missing"),
      ),
    ).sort(),
    trends: Array.from(
      new Set(
        keywords.map(
          (keyword) => keyword.metrics?.trend_direction ?? "missing",
        ),
      ),
    ).sort(),
  };
}

function numberOrMissing(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Missing";
  }
  return new Intl.NumberFormat("en-US").format(value);
}

function cpcLabel(keyword: KeywordIntelligenceKeyword): string {
  const metrics = keyword.metrics;
  if (!metrics || (metrics.cpc_low === null && metrics.cpc_high === null)) {
    return "Missing";
  }
  return moneyRange(
    metrics.cpc_low,
    metrics.cpc_high,
    metrics.currency ?? "USD",
  );
}

function scoreOrMissing(value: number | null): string {
  return value === null ? "missing" : percent(value);
}
