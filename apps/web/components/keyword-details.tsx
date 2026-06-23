"use client";

import type { EvidenceRecord, KeywordCandidate } from "@/lib/schemas";
import { percent, titleize } from "@/lib/formatters";

type Props = {
  keyword: KeywordCandidate;
  evidence: EvidenceRecord[];
};

export function KeywordDetails({ keyword, evidence }: Props) {
  const evidenceById = new Map(evidence.map((record) => [record.id, record]));
  return (
    <div className="min-w-0 space-y-3 rounded border border-gray-200 bg-gray-50 p-3 text-sm">
      <p className="break-words text-gray-700">{keyword.rationale}</p>
      <div className="grid min-w-0 gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {Object.entries(keyword.score_components).map(([name, value]) => (
          <div
            key={name}
            className="min-w-0 rounded border border-gray-200 bg-white p-2"
          >
            <dt className="break-words text-xs text-gray-500">
              {titleize(name)}
            </dt>
            <dd className="text-sm font-medium text-gray-900">
              {percent(value)}
            </dd>
          </div>
        ))}
      </div>
      <div>
        <h4 className="text-sm font-semibold text-gray-900">Evidence</h4>
        <ul className="mt-2 space-y-1">
          {keyword.evidence_ids.map((id) => {
            const record = evidenceById.get(id);
            return (
              <li key={id} className="break-words text-gray-700">
                <span className="font-medium [overflow-wrap:anywhere]">
                  {id}
                </span>
                : {record?.observation ?? "Missing evidence"}
              </li>
            );
          })}
        </ul>
      </div>
      {keyword.risk_flags.length > 0 ? (
        <p className="break-words text-amber-800">
          Risk flags: {keyword.risk_flags.join(", ")}
        </p>
      ) : null}
    </div>
  );
}
