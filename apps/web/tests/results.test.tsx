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

  it("filters keyword table by query family and expands details", async () => {
    const filters: KeywordFilterState = {
      text: "",
      queryFamily: "transactional",
      intent: "all",
      minRelevance: 0,
      minRealism: 0,
      eligibility: "all",
      sort: "relevance",
    };
    render(
      <KeywordTable
        keywords={run.keyword_candidates}
        evidence={run.product_profile.evidence}
        filters={filters}
      />,
    );
    expect(screen.getByText("buy desk lamp")).toBeInTheDocument();
    expect(
      screen.queryByText("rechargeable desk lamp"),
    ).not.toBeInTheDocument();
    await userEvent.click(
      screen.getAllByRole("button", { name: /inspect/i })[0],
    );
    expect(screen.getByText(/Transactional search query/i)).toBeInTheDocument();
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
    expect(screen.getByText("Official matches")).toBeInTheDocument();
    expect(screen.getByText("Official alternate variants")).toBeInTheDocument();
    expect(
      screen.getByText("Licensed third-party alternatives"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Other compatible alternatives"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Needs review").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", { name: "Rejected" }),
    ).toBeInTheDocument();

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
      screen.getByRole("button", { name: /accept as official match/i }),
    );
    expect(
      screen.getByText(/Local review override: Official Match/i),
    ).toBeInTheDocument();
  });

  it("renders keyword filters and emits changes", async () => {
    const onChange = vi.fn();
    const value: KeywordFilterState = {
      text: "",
      queryFamily: "all",
      intent: "all",
      minRelevance: 0,
      minRealism: 0,
      eligibility: "all",
      sort: "relevance",
    };
    render(
      <KeywordFilters
        value={value}
        queryFamilies={["transactional"]}
        intents={["commercial"]}
        onChange={onChange}
      />,
    );
    await userEvent.selectOptions(
      screen.getByLabelText(/query family/i),
      "transactional",
    );
    expect(onChange).toHaveBeenCalledWith({
      ...value,
      queryFamily: "transactional",
    });
  });

  it("copies JSON export", async () => {
    render(<JsonExport run={run} />);
    await userEvent.click(screen.getByRole("button", { name: /copy/i }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining(run.run_id),
    );
  });
});
