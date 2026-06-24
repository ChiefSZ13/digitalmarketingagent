import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { JsonExport } from "@/components/json-export";
import {
  KeywordFilters,
  type KeywordFilterState,
} from "@/components/keyword-filters";
import { KeywordTable } from "@/components/keyword-table";
import { MarketplaceSnapshotPanel } from "@/components/marketplace-snapshot-panel";
import { ProductProfilePanel } from "@/components/product-profile-panel";
import { perceptionRunSchema } from "@/lib/schemas";
import fixture from "../public/fixtures/mock-run.json";

const run = perceptionRunSchema.parse(fixture);

describe("result rendering", () => {
  it("renders product profile sections", () => {
    render(<ProductProfilePanel profile={run.product_profile} />);
    expect(
      screen.getByText("Portable Rechargeable Desk Lamp"),
    ).toBeInTheDocument();
    expect(screen.getByText("Observed Facts")).toBeInTheDocument();
    expect(screen.getByText("Unknowns")).toBeInTheDocument();
  });

  it("filters keyword table by category and expands details", async () => {
    const filters: KeywordFilterState = {
      text: "",
      category: "negative",
      intent: "all",
      minRelevance: 0,
      minConfidence: 0,
      sort: "relevance",
    };
    render(
      <KeywordTable
        keywords={run.keyword_candidates}
        evidence={run.product_profile.evidence}
        filters={filters}
      />,
    );
    expect(
      screen.getByText("cheap Portable Rechargeable Desk Lamp"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("buy Portable Rechargeable Desk Lamp"),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /inspect/i }));
    expect(screen.getByText(/Negative keyword candidate/i)).toBeInTheDocument();
  });

  it("renders marketplace snapshot estimates", () => {
    render(<MarketplaceSnapshotPanel snapshot={run.marketplace_snapshot} />);
    expect(screen.getByText("Marketplace Snapshot")).toBeInTheDocument();
    expect(screen.getByText(/Mock or non-live data/i)).toBeInTheDocument();
    expect(screen.getAllByText("Amazon")[0]).toBeInTheDocument();
    expect(screen.getByText("AliExpress")).toBeInTheDocument();
    expect(screen.getByText("$19 - $40")).toBeInTheDocument();
  });

  it("renders keyword filters and emits changes", async () => {
    const onChange = vi.fn();
    const value: KeywordFilterState = {
      text: "",
      category: "all",
      intent: "all",
      minRelevance: 0,
      minConfidence: 0,
      sort: "relevance",
    };
    render(
      <KeywordFilters
        value={value}
        categories={["negative"]}
        intents={["commercial"]}
        onChange={onChange}
      />,
    );
    await userEvent.selectOptions(
      screen.getByLabelText(/category/i),
      "negative",
    );
    expect(onChange).toHaveBeenCalledWith({ ...value, category: "negative" });
  });

  it("copies JSON export", async () => {
    render(<JsonExport run={run} />);
    await userEvent.click(screen.getByRole("button", { name: /copy/i }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining(run.run_id),
    );
  });
});
