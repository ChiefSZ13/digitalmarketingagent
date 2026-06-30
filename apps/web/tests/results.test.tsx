import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { JsonExport } from "@/components/json-export";
import { KeywordIntelligencePanel } from "@/components/keyword-intelligence-panel";
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

  it("supports review override controls for uncertain listings", async () => {
    render(<MarketplaceSnapshotPanel snapshot={run.marketplace_snapshot} />);
    await userEvent.click(
      screen.getByRole("button", { name: /accept as official match/i }),
    );
    expect(
      screen.getByText(/Review override: Official Match/i),
    ).toBeInTheDocument();
  });

  it("renders keyword intelligence metrics and missing-safe labels", () => {
    const intelligence = {
      ...run.keyword_intelligence,
      status: "complete",
      provider: "mock_keyword_metrics",
      keywords: [
        {
          text: "rechargeable desk lamp",
          normalized_text: "rechargeable desk lamp",
          origins: ["model_generated"],
          intent: "commercial",
          category: "feature",
          query_family: "feature",
          product_relevance_score: 0.9,
          confidence_score: 0.8,
          market_signal_score: 0.6,
          opportunity_score: 0.72,
          opportunity_components: {
            product_relevance: 0.9,
            market_demand: 0.55,
            competition_advantage: 0.85,
            commercial_intent: 0.62,
            cpc_efficiency: null,
            trend_signal: 0.7,
            data_completeness: 0.75,
            risk_penalty: 0,
          },
          scoring_policy_version: "keyword-opportunity-v1",
          metrics: {
            provider: "mock_keyword_metrics",
            provider_record_id: "mock-keyword-1",
            keyword: "rechargeable desk lamp",
            matched_provider_term: "rechargeable desk lamp",
            provider_match_type: "exact",
            provider_match_confidence: 1,
            average_monthly_searches: 1800,
            competition: "low",
            competition_index: 0.25,
            cpc_low: null,
            cpc_high: null,
            currency: "USD",
            monthly_history: [],
            trend_direction: "rising",
            trend_strength: 0.4,
            trend_explanation: "Recent demand increased.",
            market: "US",
            language: "en",
            retrieved_at: "2026-06-26T00:00:00Z",
            source_confidence: 0.8,
          },
          rationale: "Feature-led search query.",
          evidence_ids: ["ev-description-1"],
          risk_flags: [],
          source: "generated_from_search_concepts",
          related_to: null,
        },
      ],
    };
    render(<KeywordIntelligencePanel intelligence={intelligence} />);

    expect(screen.getByText("Keyword Intelligence")).toBeInTheDocument();
    expect(screen.getAllByText("1,800")[0]).toBeInTheDocument();
    expect(screen.getAllByText("Missing").length).toBeGreaterThan(0);
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
