"use client";

import { Copy, Download } from "lucide-react";
import type { PerceptionRun } from "@/lib/schemas";

export function JsonExport({ run }: { run: PerceptionRun }) {
  const json = JSON.stringify(run, null, 2);

  function download() {
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${run.run_id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="min-w-0 rounded border border-gray-200 bg-white p-4 sm:p-5">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-900">JSON export</h2>
        <div className="flex gap-2">
          <button
            className="inline-flex items-center gap-2 rounded border border-gray-300 px-3 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
            type="button"
            onClick={() => navigator.clipboard.writeText(json)}
          >
            <Copy aria-hidden="true" className="h-4 w-4" />
            Copy
          </button>
          <button
            className="inline-flex items-center gap-2 rounded bg-accent-600 px-3 py-2 text-sm font-medium text-white hover:bg-accent-700"
            type="button"
            onClick={download}
          >
            <Download aria-hidden="true" className="h-4 w-4" />
            Download
          </button>
        </div>
      </div>
      <pre className="mt-4 max-h-80 overflow-y-auto overflow-x-hidden whitespace-pre-wrap break-words rounded bg-gray-950 p-4 text-xs text-gray-100 [overflow-wrap:anywhere]">
        {json}
      </pre>
    </section>
  );
}
