"use client";

import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  PackageOpen,
  RotateCcw,
  XCircle,
} from "lucide-react";
import Image from "next/image";
import { type ReactNode, useMemo, useState } from "react";
import type {
  MarketplaceListingValidation,
  MarketplaceSnapshot,
} from "@/lib/schemas";
import {
  compactNumber,
  money,
  moneyRange,
  percent,
  titleize,
} from "@/lib/formatters";

type ReviewOverride =
  | "accepted"
  | "rejected"
  | "alternate_variant"
  | "alternate_package";
type GroupKey =
  | "validated"
  | "review"
  | "rejected"
  | "alternate_variant"
  | "alternate_package"
  | "alternate_condition";

const GROUPS: Array<{
  key: GroupKey;
  title: string;
  empty: string;
}> = [
  {
    key: "validated",
    title: "Validated matches",
    empty: "No validated primary matches.",
  },
  {
    key: "review",
    title: "Needs review",
    empty: "No listings need review.",
  },
  {
    key: "rejected",
    title: "Rejected listings",
    empty: "No rejected listings.",
  },
  {
    key: "alternate_variant",
    title: "Alternate variants",
    empty: "No alternate variants.",
  },
  {
    key: "alternate_package",
    title: "Alternate package quantities",
    empty: "No alternate package quantities.",
  },
  {
    key: "alternate_condition",
    title: "Alternate conditions",
    empty: "No alternate conditions.",
  },
];

export function MarketplaceSnapshotPanel({
  snapshot,
}: {
  snapshot: MarketplaceSnapshot;
}) {
  const [overrides, setOverrides] = useState<Record<string, ReviewOverride>>(
    {},
  );
  const grouped = useMemo(
    () => groupListings(snapshot.validated_listings, overrides),
    [snapshot.validated_listings, overrides],
  );

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

      {snapshot.validation_summary ? (
        <div className="mt-4 grid min-w-0 gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <SummaryMetric
            label="Candidates"
            value={snapshot.validation_summary.total_candidates}
          />
          <SummaryMetric
            label="Primary eligible"
            value={snapshot.validation_summary.primary_eligible_count}
          />
          <SummaryMetric
            label="Needs review"
            value={snapshot.validation_summary.uncertain_count}
          />
          <SummaryMetric
            label="Rejected"
            value={snapshot.validation_summary.rejected_count}
          />
        </div>
      ) : null}

      <div className="mt-5 grid min-w-0 gap-5 2xl:grid-cols-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-900">
            Platform ranking
          </h3>
          {snapshot.platform_rankings.length > 0 ? (
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
                        {platform.validated_listing_count} validated ·{" "}
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
          ) : (
            <EmptyState message="No validated platforms were eligible for primary ranking." />
          )}
        </div>

        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-900">Price ranges</h3>
          {snapshot.price_estimates.length > 0 ? (
            <div className="mt-3 overflow-hidden rounded border border-gray-200">
              <table className="w-full table-fixed text-left text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="w-[32%] px-3 py-2 font-medium">Platform</th>
                    <th className="w-[28%] px-3 py-2 font-medium">Range</th>
                    <th className="w-[40%] px-3 py-2 font-medium">Basis</th>
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
                        {price.price_median !== null ? (
                          <span className="block text-xs text-gray-500">
                            median {money(price.price_median, price.currency)}
                          </span>
                        ) : null}
                      </td>
                      <td className="px-3 py-3 text-xs text-gray-600">
                        <span className="break-words">
                          {price.observed_offer_count ?? 0} validated offers ·{" "}
                          {price.price_basis}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState message="No validated primary offers were eligible for price aggregation." />
          )}
        </div>
      </div>

      <div className="mt-5 min-w-0">
        <h3 className="text-sm font-semibold text-gray-900">
          Product validation
        </h3>
        <div className="mt-3 grid min-w-0 gap-4 xl:grid-cols-2">
          {GROUPS.map((group) => (
            <ValidationGroup
              key={group.key}
              title={group.title}
              empty={group.empty}
              listings={grouped[group.key]}
              overrides={overrides}
              onOverride={(listingId, override) =>
                setOverrides((current) => ({
                  ...current,
                  [listingId]: override,
                }))
              }
            />
          ))}
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

function ValidationGroup({
  title,
  empty,
  listings,
  overrides,
  onOverride,
}: {
  title: string;
  empty: string;
  listings: MarketplaceListingValidation[];
  overrides: Record<string, ReviewOverride>;
  onOverride: (listingId: string, override: ReviewOverride) => void;
}) {
  return (
    <section className="min-w-0 rounded border border-gray-200">
      <div className="flex items-center justify-between gap-3 border-b border-gray-100 px-3 py-2">
        <h4 className="text-sm font-semibold text-gray-900">{title}</h4>
        <span className="rounded border border-gray-200 px-2 py-0.5 text-xs text-gray-600">
          {listings.length}
        </span>
      </div>
      <div className="min-w-0 divide-y divide-gray-100">
        {listings.length > 0 ? (
          listings.map((validation) => (
            <ListingRow
              key={validation.listing.listing_id}
              validation={validation}
              override={overrides[validation.listing.listing_id]}
              onOverride={onOverride}
            />
          ))
        ) : (
          <EmptyState message={empty} />
        )}
      </div>
    </section>
  );
}

function ListingRow({
  validation,
  override,
  onOverride,
}: {
  validation: MarketplaceListingValidation;
  override: ReviewOverride | undefined;
  onOverride: (listingId: string, override: ReviewOverride) => void;
}) {
  const { listing, match_result: match } = validation;
  const imageUrl = listing.image_urls[0];
  return (
    <article className="min-w-0 p-3">
      <div className="flex min-w-0 gap-3">
        {imageUrl ? (
          <Image
            alt=""
            className="h-14 w-14 flex-none rounded border border-gray-200 object-cover"
            height={56}
            src={imageUrl}
            unoptimized
            width={56}
          />
        ) : (
          <div className="flex h-14 w-14 flex-none items-center justify-center rounded border border-gray-200 bg-gray-50">
            <PackageOpen aria-hidden="true" className="h-5 w-5 text-gray-400" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="break-words text-sm font-semibold text-gray-900">
                {listing.title}
              </p>
              <p className="mt-1 break-words text-xs text-gray-500">
                {listing.provider} · {listing.platform}
                {listing.seller_name ? ` · ${listing.seller_name}` : ""}
              </p>
            </div>
            <StatusBadge status={match.status} score={match.score} />
          </div>

          <dl className="mt-3 grid min-w-0 gap-2 text-xs text-gray-600 sm:grid-cols-2">
            <Fact
              label="Item"
              value={money(listing.item_price, listing.currency)}
            />
            <Fact
              label="Shipping"
              value={money(listing.shipping_price, listing.currency)}
            />
            <Fact
              label="Landed"
              value={money(listing.landed_price, listing.currency)}
            />
            <Fact
              label="Condition"
              value={titleize(listing.condition ?? "unknown")}
            />
            <Fact
              label="Observed"
              value={new Date(listing.observed_at).toLocaleString()}
            />
            <Fact
              label="Matched"
              value={
                match.matched_fields.length > 0
                  ? match.matched_fields.map(titleize).join(", ")
                  : "None"
              }
            />
          </dl>

          {override ? (
            <p className="mt-3 inline-flex rounded border border-blue-200 bg-blue-50 px-2 py-1 text-xs font-medium text-blue-800">
              Local review override: {titleize(override)}
            </p>
          ) : null}

          {match.requires_human_review ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <ReviewButton
                icon={
                  <CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5" />
                }
                label="Accept as match"
                onClick={() => onOverride(listing.listing_id, "accepted")}
              />
              <ReviewButton
                icon={<XCircle aria-hidden="true" className="h-3.5 w-3.5" />}
                label="Reject"
                onClick={() => onOverride(listing.listing_id, "rejected")}
              />
              <ReviewButton
                icon={<RotateCcw aria-hidden="true" className="h-3.5 w-3.5" />}
                label="Alternate variant"
                onClick={() =>
                  onOverride(listing.listing_id, "alternate_variant")
                }
              />
              <ReviewButton
                icon={
                  <PackageOpen aria-hidden="true" className="h-3.5 w-3.5" />
                }
                label="Alternate package"
                onClick={() =>
                  onOverride(listing.listing_id, "alternate_package")
                }
              />
            </div>
          ) : null}

          <details className="mt-3 min-w-0">
            <summary className="cursor-pointer text-xs font-medium text-accent-700 outline-none focus-visible:ring-2 focus-visible:ring-accent-500">
              Why was this classified this way?
            </summary>
            <div className="mt-2 min-w-0 space-y-2 rounded border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
              <p className="break-words">{match.human_summary}</p>
              <p className="break-words">
                Reason codes:{" "}
                {match.reason_codes.length > 0
                  ? match.reason_codes.join(", ")
                  : "None"}
              </p>
              {match.conflicts.length > 0 ? (
                <ul className="space-y-1">
                  {match.conflicts.map((conflict) => (
                    <li
                      key={`${listing.listing_id}-${conflict.code}-${conflict.field}`}
                      className="break-words"
                    >
                      {conflict.code}: {conflict.explanation}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No hard conflicts detected.</p>
              )}
            </div>
          </details>
        </div>
      </div>
    </article>
  );
}

function StatusBadge({ status, score }: { status: string; score: number }) {
  const label = titleize(status);
  const tone =
    status === "exact_match" || status === "probable_match"
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : status === "uncertain"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-red-200 bg-red-50 text-red-800";
  const Icon =
    status === "exact_match" || status === "probable_match"
      ? CheckCircle2
      : status === "uncertain"
        ? HelpCircle
        : XCircle;
  return (
    <span
      className={`inline-flex flex-none items-center gap-1 rounded border px-2 py-1 text-xs font-medium ${tone}`}
    >
      <Icon aria-hidden="true" className="h-3.5 w-3.5" />
      {label} · {percent(score)}
    </span>
  );
}

function ReviewButton({
  icon,
  label,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
      onClick={onClick}
      type="button"
    >
      {icon}
      {label}
    </button>
  );
}

function SummaryMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="min-w-0 rounded border border-gray-200 px-3 py-2">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="font-medium text-gray-500">{label}</dt>
      <dd className="mt-0.5 break-words text-gray-800">{value}</dd>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="min-w-0 p-3 text-sm text-gray-500">
      <p className="break-words">{message}</p>
    </div>
  );
}

function groupListings(
  listings: MarketplaceListingValidation[],
  overrides: Record<string, ReviewOverride>,
): Record<GroupKey, MarketplaceListingValidation[]> {
  const grouped: Record<GroupKey, MarketplaceListingValidation[]> = {
    validated: [],
    review: [],
    rejected: [],
    alternate_variant: [],
    alternate_package: [],
    alternate_condition: [],
  };
  for (const validation of listings) {
    const listingId = validation.listing.listing_id;
    const override = overrides[listingId];
    if (override === "accepted") {
      grouped.validated.push(validation);
      continue;
    }
    if (override === "rejected") {
      grouped.rejected.push(validation);
      continue;
    }
    if (override === "alternate_variant") {
      grouped.alternate_variant.push(validation);
      continue;
    }
    if (override === "alternate_package") {
      grouped.alternate_package.push(validation);
      continue;
    }

    const group = validation.match_result.aggregation_group;
    if (group === "alternate_variant") {
      grouped.alternate_variant.push(validation);
    } else if (group === "alternate_package") {
      grouped.alternate_package.push(validation);
    } else if (group === "alternate_condition") {
      grouped.alternate_condition.push(validation);
    } else if (
      validation.match_result.status === "exact_match" ||
      validation.match_result.status === "probable_match"
    ) {
      grouped.validated.push(validation);
    } else if (validation.match_result.status === "uncertain") {
      grouped.review.push(validation);
    } else {
      grouped.rejected.push(validation);
    }
  }
  return grouped;
}
