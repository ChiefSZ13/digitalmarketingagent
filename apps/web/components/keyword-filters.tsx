"use client";

import { Search } from "lucide-react";

export type KeywordFilterState = {
  text: string;
  queryFamily: string;
  intent: string;
  minRelevance: number;
  minRealism: number;
  eligibility: "all" | "eligible" | "not_eligible";
  sort: "relevance" | "realism" | "text";
};

type Props = {
  value: KeywordFilterState;
  queryFamilies: string[];
  intents: string[];
  onChange: (value: KeywordFilterState) => void;
};

export function KeywordFilters({
  value,
  queryFamilies,
  intents,
  onChange,
}: Props) {
  return (
    <div className="min-w-0 rounded border border-gray-200 bg-white p-4">
      <div className="grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-7">
        <label className="min-w-0 sm:col-span-2 xl:col-span-2">
          <span className="block text-sm font-medium text-gray-900">
            Search keywords
          </span>
          <span className="mt-2 flex min-w-0 items-center rounded border border-gray-300 px-3">
            <Search aria-hidden="true" className="h-4 w-4 text-gray-500" />
            <input
              className="min-w-0 flex-1 border-0 px-2 py-2 text-sm outline-none"
              type="search"
              value={value.text}
              onChange={(event) =>
                onChange({ ...value, text: event.target.value })
              }
            />
          </span>
        </label>
        <Select
          label="Query family"
          value={value.queryFamily}
          options={queryFamilies}
          onChange={(queryFamily) => onChange({ ...value, queryFamily })}
        />
        <Select
          label="Intent"
          value={value.intent}
          options={intents}
          onChange={(intent) => onChange({ ...value, intent })}
        />
        <Select
          label="Sort"
          value={value.sort}
          options={["relevance", "realism", "text"]}
          onChange={(sort) =>
            onChange({ ...value, sort: sort as KeywordFilterState["sort"] })
          }
        />
        <Select
          label="Eligibility"
          value={value.eligibility}
          options={["eligible", "not_eligible"]}
          onChange={(eligibility) =>
            onChange({
              ...value,
              eligibility: eligibility as KeywordFilterState["eligibility"],
            })
          }
        />
        <label className="min-w-0">
          <span className="block text-sm font-medium text-gray-900">
            Min product relevance
          </span>
          <input
            className="mt-2 w-full"
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={value.minRelevance}
            onChange={(event) =>
              onChange({ ...value, minRelevance: Number(event.target.value) })
            }
          />
        </label>
        <label className="min-w-0">
          <span className="block text-sm font-medium text-gray-900">
            Min query realism
          </span>
          <input
            className="mt-2 w-full"
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={value.minRealism}
            onChange={(event) =>
              onChange({ ...value, minRealism: Number(event.target.value) })
            }
          />
        </label>
      </div>
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
            {option.replaceAll("_", " ")}
          </option>
        ))}
      </select>
    </label>
  );
}
