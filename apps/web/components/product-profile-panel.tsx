"use client";

import type { EvidenceLinkedText, ProductProfile } from "@/lib/schemas";
import { percent, titleize } from "@/lib/formatters";

type Props = {
  profile: ProductProfile;
};

export function ProductProfilePanel({ profile }: Props) {
  const sections: Array<[string, EvidenceLinkedText[]]> = [
    ["Observed Facts", profile.observed_facts],
    ["User-Provided Facts", profile.user_provided_facts],
    ["Inferred Attributes", profile.inferred_attributes],
    ["Features", profile.features],
    ["Benefits", profile.benefits],
    ["Use Cases", profile.use_cases],
    ["Target Audiences", profile.target_audiences],
    ["Unknowns", profile.unknowns],
    ["Ambiguities", profile.ambiguities],
  ];

  return (
    <section className="min-w-0 rounded border border-gray-200 bg-white p-4 sm:p-5">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-gray-900">
            {profile.product_name?.value ?? "Product profile"}
          </h2>
          <p className="mt-1 break-words text-sm text-gray-600">
            {profile.summary.value}
          </p>
        </div>
        <span className="rounded border border-gray-200 px-2 py-1 text-xs font-medium text-gray-700">
          Confidence {percent(profile.overall_confidence)}
        </span>
      </div>
      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <SummaryItem label="Brand" value={profile.brand?.value ?? "Unknown"} />
        <SummaryItem
          label="Category"
          value={profile.category?.value ?? "Unknown"}
        />
        <SummaryItem
          label="Subcategory"
          value={profile.subcategory?.value ?? "Unknown"}
        />
      </dl>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {sections.map(([title, values]) => (
          <ProfileSection key={title} title={title} values={values} />
        ))}
      </div>
      <div className="mt-5">
        <h3 className="text-sm font-semibold text-gray-900">Claim Warnings</h3>
        {profile.claim_flags.length > 0 ? (
          <ul className="mt-2 space-y-2">
            {profile.claim_flags.map((flag) => (
              <li
                key={`${flag.claim}-${flag.reason}`}
                className="min-w-0 rounded border border-amber-200 bg-amber-50 p-3 text-sm"
              >
                <span className="font-medium text-amber-900">
                  {titleize(flag.severity)}:
                </span>{" "}
                <span className="break-words text-amber-900">{flag.claim}</span>
                <p className="mt-1 break-words text-amber-800">{flag.reason}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-gray-600">
            No unsafe or unverified claim flags.
          </p>
        )}
      </div>
    </section>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded border border-gray-200 p-3">
      <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm text-gray-900">{value}</dd>
    </div>
  );
}

function ProfileSection({
  title,
  values,
}: {
  title: string;
  values: EvidenceLinkedText[];
}) {
  return (
    <section className="min-w-0 rounded border border-gray-200 p-3">
      <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      {values.length > 0 ? (
        <ul className="mt-2 space-y-2">
          {values.map((value) => (
            <li
              key={`${title}-${value.value}`}
              className="min-w-0 break-words text-sm text-gray-700"
            >
              {value.value}
              <span className="ml-2 text-xs text-gray-500">
                {percent(value.confidence)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-gray-500">None reported.</p>
      )}
    </section>
  );
}
