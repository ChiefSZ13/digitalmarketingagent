import { render, screen, within } from "@testing-library/react";
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

  it("renders marketplace validation groups and conflict explanations", async () => {
    render(<MarketplaceSnapshotPanel snapshot={run.marketplace_snapshot} />);
    expect(screen.getByText("Validated matches")).toBeInTheDocument();
    expect(screen.getAllByText("Needs review").length).toBeGreaterThan(0);
    expect(screen.getByText("Rejected listings")).toBeInTheDocument();
    expect(
      screen.getByText("Alternate package quantities"),
    ).toBeInTheDocument();
    expect(screen.getByText("Alternate conditions")).toBeInTheDocument();

    await userEvent.click(
      screen.getAllByText("Why was this classified this way?")[0],
    );
    expect(screen.getAllByText(/Reason codes:/i).length).toBeGreaterThan(0);
    expect(
      screen.getAllByText(/No hard conflicts detected/i).length,
    ).toBeGreaterThan(0);

    const rejectedRow = screen
      .getByText("Replacement charger for Portable Rechargeable Desk Lamp")
      .closest("article");
    expect(rejectedRow).not.toBeNull();
    await userEvent.click(
      within(rejectedRow as HTMLElement).getByText(
        "Why was this classified this way?",
      ),
    );
    expect(screen.getAllByText(/ACCESSORY_MISMATCH/i).length).toBeGreaterThan(
      0,
    );
  });

  it("supports local review override controls for uncertain listings", async () => {
    render(<MarketplaceSnapshotPanel snapshot={run.marketplace_snapshot} />);
    await userEvent.click(
      screen.getByRole("button", { name: /accept as match/i }),
    );
    expect(
      screen.getByText(/Local review override: Accepted/i),
    ).toBeInTheDocument();
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
